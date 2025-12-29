"""
Embedding generation utilities.
Supports both OpenAI and local Sentence Transformers.
"""

from typing import List, Union
import numpy as np
from functools import lru_cache
from loguru import logger

from src.config import config


class EmbeddingGenerator:
    """Generate embeddings using OpenAI or Sentence Transformers."""
    
    def __init__(self, use_openai: bool = None):
        """
        Initialize embedding generator.
        
        Args:
            use_openai: If True, use OpenAI. If False, use Sentence Transformers.
                       If None, use OpenAI if API key available, else local.
        """
        if use_openai is None:
            use_openai = bool(config.OPENAI_API_KEY)
        
        self.use_openai = use_openai
        
        if self.use_openai:
            from openai import OpenAI
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.model = config.OPENAI_EMBEDDING_MODEL
            logger.info(f"Using OpenAI embeddings: {self.model}")
        else:
            from sentence_transformers import SentenceTransformer
            self.model_name = config.SENTENCE_TRANSFORMER_MODEL
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Using Sentence Transformers: {self.model_name}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.embed_batch([text])[0]
    
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        if self.use_openai:
            return self._embed_batch_openai(texts)
        else:
            return self._embed_batch_local(texts)
    
    def _embed_batch_openai(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings using OpenAI API."""
        try:
            # Clean texts
            texts = [text.replace("\n", " ")[:8000] for text in texts]
            
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            embeddings = [np.array(item.embedding) for item in response.data]
            return embeddings
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise
    
    def _embed_batch_local(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings using Sentence Transformers."""
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return [emb for emb in embeddings]
            
        except Exception as e:
            logger.error(f"Local embedding error: {e}")
            raise
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self.use_openai:
            # text-embedding-3-small: 1536, text-embedding-ada-002: 1536
            return 1536 if "3" in self.model else 1536
        else:
            # all-MiniLM-L6-v2: 384
            return self.model.get_sentence_embedding_dimension()


# Global embedding generator instance - proper singleton with lru_cache
_embedding_generator = None
_embedding_generator_lock = None


@lru_cache(maxsize=1)
def get_embedding_generator() -> EmbeddingGenerator:
    """
    Get or create global embedding generator.
    
    Uses lru_cache for proper singleton behavior - model is loaded only once
    and reused across all calls. This prevents the 400MB Sentence Transformer
    model from being loaded multiple times.
    """
    logger.info("Creating singleton EmbeddingGenerator instance")
    return EmbeddingGenerator()


def reset_embedding_generator():
    """
    Reset the cached embedding generator.
    
    Useful for testing or when switching between OpenAI and local embeddings.
    """
    get_embedding_generator.cache_clear()
    global _embedding_generator
    _embedding_generator = None

