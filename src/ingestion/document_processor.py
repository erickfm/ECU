"""
Document processor for ingesting OCR text files into observation store.

Follows the observation-first principle: treat each chunk as an independent observation.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re
from loguru import logger
from tqdm import tqdm

from src.config import config
from src.database import Observation, ObservationCooccurrence, get_session
from src.utils.embeddings import get_embedding_generator


class DocumentProcessor:
    """Process documents and extract observations."""
    
    def __init__(self, engine):
        self.engine = engine
        self.embedding_gen = get_embedding_generator()
        self.chunk_size = config.CHUNK_SIZE
        self.chunk_overlap = config.CHUNK_OVERLAP
        
    def process_directory(self, directory: Path, limit: Optional[int] = None):
        """
        Process all text files in a directory.
        
        Args:
            directory: Path to directory containing text files
            limit: Optional limit on number of files to process
        """
        # Find all .txt files
        txt_files = list(directory.rglob("*.txt"))
        
        if limit:
            txt_files = txt_files[:limit]
        
        logger.info(f"Found {len(txt_files)} text files to process")
        
        # Process in batches
        batch_size = 100
        for i in tqdm(range(0, len(txt_files), batch_size), desc="Processing batches"):
            batch = txt_files[i:i+batch_size]
            self._process_batch(batch)
            
        logger.info(f"Completed processing {len(txt_files)} files")
    
    def _process_batch(self, files: List[Path]):
        """
        Process a batch of files with sub-batching for memory efficiency.
        
        Uses configurable sub-batch size and flush threshold to prevent
        memory accumulation during large ingestion runs.
        """
        session = get_session(self.engine)
        
        SUB_BATCH_SIZE = config.INGESTION_SUB_BATCH_SIZE
        FLUSH_THRESHOLD = config.INGESTION_FLUSH_THRESHOLD
        
        try:
            pending_observations = []
            total_processed = 0
            
            # Process files in sub-batches
            for i in range(0, len(files), SUB_BATCH_SIZE):
                sub_batch = files[i:i + SUB_BATCH_SIZE]
                
                for file_path in sub_batch:
                    observations = self._process_file(file_path)
                    pending_observations.extend(observations)
                    
                    # Flush to database when threshold reached
                    if len(pending_observations) >= FLUSH_THRESHOLD:
                        if pending_observations:
                            session.bulk_save_objects(pending_observations)
                            session.commit()
                            self._create_cooccurrences(session, pending_observations)
                            total_processed += len(pending_observations)
                            logger.debug(f"Flushed {len(pending_observations)} observations (total: {total_processed})")
                            pending_observations = []
            
            # Flush remaining observations
            if pending_observations:
                session.bulk_save_objects(pending_observations)
                session.commit()
                self._create_cooccurrences(session, pending_observations)
                total_processed += len(pending_observations)
                logger.debug(f"Final flush: {len(pending_observations)} observations (total: {total_processed})")
                
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            session.rollback()
        finally:
            session.close()
    
    def _process_file(self, file_path: Path) -> List[Observation]:
        """
        Process a single file and create observations.
        
        Args:
            file_path: Path to text file
            
        Returns:
            List of Observation objects (not yet committed)
        """
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Extract doc_id from filename
            doc_id = file_path.stem  # e.g., HOUSE_OVERSIGHT_010477.jpg
            
            # Try to extract timestamp from content or use file modification time
            doc_timestamp = self._extract_timestamp(content, file_path)
            
            # Chunk the document
            chunks = self._chunk_document(content)
            
            # Create observations for each chunk
            observations = []
            
            # Generate embeddings in batch
            if chunks:
                chunk_texts = [chunk['text'] for chunk in chunks]
                embeddings = self.embedding_gen.embed_batch(chunk_texts)
                
                for chunk, embedding in zip(chunks, embeddings):
                    obs = Observation(
                        doc_id=doc_id,
                        span_start=chunk['start'],
                        span_end=chunk['end'],
                        surface_form=self._extract_surface_forms(chunk['text']),
                        context=chunk['text'],
                        embedding=embedding.tolist(),  # pgvector handles list conversion
                        doc_timestamp=doc_timestamp,
                        source_reliability=1.0,
                        meta_data={
                            'file_path': str(file_path),
                            'chunk_index': chunk['index'],
                            'total_chunks': len(chunks),
                        }
                    )
                    observations.append(obs)
            
            return observations
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return []
    
    def _chunk_document(self, content: str) -> List[Dict]:
        """
        Split document into overlapping chunks.
        
        Args:
            content: Document text
            
        Returns:
            List of chunk dictionaries with text, start, end, index
        """
        # Clean content
        content = content.strip()
        
        if len(content) < config.MIN_OBSERVATION_LENGTH:
            return []
        
        chunks = []
        words = content.split()
        
        i = 0
        chunk_index = 0
        
        while i < len(words):
            # Take chunk_size words
            chunk_words = words[i:i+self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            # Skip if too short
            if len(chunk_text) >= config.MIN_OBSERVATION_LENGTH:
                # Calculate character positions (approximate)
                start_pos = len(' '.join(words[:i]))
                end_pos = start_pos + len(chunk_text)
                
                chunks.append({
                    'text': chunk_text,
                    'start': start_pos,
                    'end': end_pos,
                    'index': chunk_index
                })
                chunk_index += 1
            
            # Move forward with overlap
            i += (self.chunk_size - self.chunk_overlap)
        
        return chunks
    
    def _extract_surface_forms(self, text: str) -> Optional[str]:
        """
        Extract key surface forms (names, entities) from text.
        Simplified version - just return key terms.
        
        Args:
            text: Text to extract from
            
        Returns:
            Comma-separated surface forms or None
        """
        # Simple extraction: capitalized words (potential names)
        words = text.split()
        capitalized = [w for w in words if w and w[0].isupper() and len(w) > 2]
        
        # Get unique, limit to first 10
        unique_caps = list(dict.fromkeys(capitalized))[:10]
        
        return ', '.join(unique_caps) if unique_caps else None
    
    def _extract_timestamp(self, content: str, file_path: Path) -> Optional[datetime]:
        """
        Try to extract timestamp from content, otherwise use file mtime.
        
        Args:
            content: Document content
            file_path: Path to file
            
        Returns:
            Datetime object or None
        """
        # Look for date patterns in content
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY
            r'\d{4}-\d{2}-\d{2}',       # YYYY-MM-DD
            r'[A-Z][a-z]+ \d{1,2},? \d{4}',  # Month DD, YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    from dateutil import parser
                    return parser.parse(match.group())
                except:
                    pass
        
        # Fallback to file modification time
        try:
            return datetime.fromtimestamp(file_path.stat().st_mtime)
        except:
            return None
    
    def _create_cooccurrences(self, session, observations: List[Observation]):
        """
        Create co-occurrence relationships between observations in the same document.
        
        Args:
            session: Database session
            observations: List of observations from same batch
        """
        # Group by document
        doc_groups = {}
        for obs in observations:
            if obs.doc_id not in doc_groups:
                doc_groups[obs.doc_id] = []
            doc_groups[obs.doc_id].append(obs)
        
        cooccurrences = []
        
        # For each document, create co-occurrences between adjacent chunks
        for doc_id, doc_obs in doc_groups.items():
            for i in range(len(doc_obs) - 1):
                obs_a = doc_obs[i]
                obs_b = doc_obs[i + 1]
                
                # Calculate distance (character difference)
                distance = abs(obs_b.span_start - obs_a.span_end) if (obs_a.span_start and obs_b.span_start) else None
                
                cooc = ObservationCooccurrence(
                    obs_a_id=obs_a.id,
                    obs_b_id=obs_b.id,
                    distance=distance,
                    doc_id=doc_id,
                    co_occurrence_type='adjacent_chunks',
                    strength=1.0,
                    metadata={}
                )
                cooccurrences.append(cooc)
        
        # Bulk insert co-occurrences
        if cooccurrences:
            session.bulk_save_objects(cooccurrences)
            session.commit()

