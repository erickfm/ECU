"""
Tool layer for observation retrieval.

Following spec: semantic_search, find_cooccurrences, temporal_query, 
traverse_graph, cluster_observations, find_contradictions.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy import func, and_, or_, text
from loguru import logger
import numpy as np

from src.database import Observation, ObservationCooccurrence, get_session
from src.utils.embeddings import get_embedding_generator
from src.config import config


class RetrievalTools:
    """Tools for retrieving observations from the store."""
    
    def __init__(self, engine):
        self.engine = engine
        self.embedding_gen = get_embedding_generator()
    
    def semantic_search(
        self, 
        query: str, 
        k: int = None,
        min_similarity: float = 0.0,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Semantic search over observations using vector similarity.
        
        Args:
            query: Search query text
            k: Number of results to return (default: config.SEMANTIC_SEARCH_K)
            min_similarity: Minimum cosine similarity threshold
            filters: Optional filters (doc_id, date_range, etc.)
            
        Returns:
            List of observation dictionaries with similarity scores
        """
        k = k or config.SEMANTIC_SEARCH_K
        session = get_session(self.engine)
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_gen.embed_text(query)
            
            # Build query with pgvector distance operator
            from pgvector.sqlalchemy import Vector
            query_obj = session.query(
                Observation,
                Observation.embedding.cosine_distance(query_embedding).label('distance')
            )
            
            # Apply filters
            if filters:
                if 'doc_id' in filters:
                    query_obj = query_obj.filter(Observation.doc_id == filters['doc_id'])
                if 'start_date' in filters and 'end_date' in filters:
                    query_obj = query_obj.filter(
                        and_(
                            Observation.doc_timestamp >= filters['start_date'],
                            Observation.doc_timestamp <= filters['end_date']
                        )
                    )
            
            # Order by similarity and limit
            results = query_obj.order_by('distance').limit(k).all()
            
            # Convert to dictionaries
            observations = []
            for obs, distance in results:
                similarity = 1 - distance  # Convert distance to similarity
                
                if similarity >= min_similarity:
                    observations.append({
                        'id': obs.id,
                        'doc_id': obs.doc_id,
                        'context': obs.context,
                        'surface_form': obs.surface_form,
                        'similarity': float(similarity),
                        'timestamp': obs.doc_timestamp.isoformat() if obs.doc_timestamp else None,
                        'metadata': dict(obs.metadata) if obs.metadata else {},
                    })
            
            logger.info(f"Semantic search for '{query[:50]}...' returned {len(observations)} results")
            return observations
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []
        finally:
            session.close()
    
    def find_cooccurrences(
        self,
        surface_form: str = None,
        observation_id: int = None,
        max_distance: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Find observations that co-occur with a given surface form or observation.
        
        Args:
            surface_form: Surface form to search for
            observation_id: Observation ID to find co-occurrences for
            max_distance: Maximum distance between observations
            limit: Maximum number of results
            
        Returns:
            List of co-occurring observations with relationship info
        """
        session = get_session(self.engine)
        
        try:
            results = []
            
            if observation_id:
                # Direct co-occurrence lookup
                query = session.query(
                    ObservationCooccurrence,
                    Observation
                ).join(
                    Observation,
                    or_(
                        Observation.id == ObservationCooccurrence.obs_b_id,
                        Observation.id == ObservationCooccurrence.obs_a_id
                    )
                ).filter(
                    or_(
                        ObservationCooccurrence.obs_a_id == observation_id,
                        ObservationCooccurrence.obs_b_id == observation_id
                    )
                )
                
                if max_distance:
                    query = query.filter(ObservationCooccurrence.distance <= max_distance)
                
                coocs = query.limit(limit).all()
                
                for cooc, obs in coocs:
                    results.append({
                        'id': obs.id,
                        'doc_id': obs.doc_id,
                        'context': obs.context,
                        'surface_form': obs.surface_form,
                        'distance': cooc.distance,
                        'co_occurrence_type': cooc.co_occurrence_type,
                        'strength': cooc.strength,
                        'metadata': dict(obs.metadata) if obs.metadata else {},
                    })
            
            elif surface_form:
                # Find observations with this surface form, then their co-occurrences
                obs_with_form = session.query(Observation).filter(
                    Observation.surface_form.like(f"%{surface_form}%")
                ).limit(10).all()
                
                for obs in obs_with_form:
                    coocs = self.find_cooccurrences(observation_id=obs.id, max_distance=max_distance, limit=limit)
                    results.extend(coocs)
            
            logger.info(f"Found {len(results)} co-occurrences")
            return results
            
        except Exception as e:
            logger.error(f"Find co-occurrences error: {e}")
            return []
        finally:
            session.close()
    
    def temporal_query(
        self,
        surface_form: str = None,
        keyword: str = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Query observations within a temporal window.
        
        Args:
            surface_form: Surface form to search for
            keyword: Keyword to search in context
            start_date: Start of time range
            end_date: End of time range
            limit: Maximum results
            
        Returns:
            List of observations ordered by timestamp
        """
        session = get_session(self.engine)
        
        try:
            query = session.query(Observation)
            
            # Apply temporal filters
            if start_date:
                query = query.filter(Observation.doc_timestamp >= start_date)
            if end_date:
                query = query.filter(Observation.doc_timestamp <= end_date)
            
            # Apply content filters
            if surface_form:
                query = query.filter(Observation.surface_form.like(f"%{surface_form}%"))
            if keyword:
                query = query.filter(Observation.context.like(f"%{keyword}%"))
            
            # Order by time and limit
            results = query.order_by(Observation.doc_timestamp).limit(limit).all()
            
            observations = [{
                'id': obs.id,
                'doc_id': obs.doc_id,
                'context': obs.context,
                'surface_form': obs.surface_form,
                'timestamp': obs.doc_timestamp.isoformat() if obs.doc_timestamp else None,
                'metadata': dict(obs.metadata) if obs.metadata else {},
            } for obs in results]
            
            logger.info(f"Temporal query returned {len(observations)} results")
            return observations
            
        except Exception as e:
            logger.error(f"Temporal query error: {e}")
            return []
        finally:
            session.close()
    
    def traverse_graph(
        self,
        start_observation_id: int,
        max_hops: int = 2,
        min_strength: float = 0.5
    ) -> List[Dict]:
        """
        Traverse co-occurrence graph from a starting observation.
        
        Args:
            start_observation_id: Starting observation ID
            max_hops: Maximum number of hops to traverse
            min_strength: Minimum co-occurrence strength
            
        Returns:
            List of observations reachable within max_hops
        """
        session = get_session(self.engine)
        
        try:
            visited = set()
            current_level = {start_observation_id}
            all_observations = []
            
            for hop in range(max_hops):
                next_level = set()
                
                for obs_id in current_level:
                    if obs_id in visited:
                        continue
                    
                    visited.add(obs_id)
                    
                    # Get observation
                    obs = session.query(Observation).filter(Observation.id == obs_id).first()
                    if obs:
                        all_observations.append({
                            'id': obs.id,
                            'doc_id': obs.doc_id,
                            'context': obs.context,
                            'surface_form': obs.surface_form,
                            'hop_distance': hop,
                            'metadata': dict(obs.metadata) if obs.metadata else {},
                        })
                    
                    # Find neighbors
                    neighbors = session.query(ObservationCooccurrence).filter(
                        or_(
                            ObservationCooccurrence.obs_a_id == obs_id,
                            ObservationCooccurrence.obs_b_id == obs_id
                        ),
                        ObservationCooccurrence.strength >= min_strength
                    ).all()
                    
                    for neighbor in neighbors:
                        other_id = neighbor.obs_b_id if neighbor.obs_a_id == obs_id else neighbor.obs_a_id
                        if other_id not in visited:
                            next_level.add(other_id)
                
                current_level = next_level
                
                if not current_level:
                    break
            
            logger.info(f"Graph traversal found {len(all_observations)} observations in {hop+1} hops")
            return all_observations
            
        except Exception as e:
            logger.error(f"Graph traversal error: {e}")
            return []
        finally:
            session.close()
    
    def cluster_observations(
        self,
        observation_ids: List[int],
        similarity_threshold: float = 0.7
    ) -> List[List[int]]:
        """
        Cluster observations by embedding similarity.
        
        Args:
            observation_ids: List of observation IDs to cluster
            similarity_threshold: Minimum similarity for same cluster
            
        Returns:
            List of clusters (each cluster is a list of observation IDs)
        """
        session = get_session(self.engine)
        
        try:
            # Get observations with embeddings
            observations = session.query(Observation).filter(
                Observation.id.in_(observation_ids)
            ).all()
            
            if not observations:
                return []
            
            # Extract embeddings
            embeddings = np.array([obs.embedding for obs in observations])
            obs_ids = [obs.id for obs in observations]
            
            # Simple greedy clustering
            clusters = []
            assigned = set()
            
            for i, obs_id in enumerate(obs_ids):
                if obs_id in assigned:
                    continue
                
                # Start new cluster
                cluster = [obs_id]
                assigned.add(obs_id)
                
                # Find similar observations
                for j, other_id in enumerate(obs_ids):
                    if other_id in assigned:
                        continue
                    
                    # Compute cosine similarity
                    sim = np.dot(embeddings[i], embeddings[j]) / (
                        np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                    )
                    
                    if sim >= similarity_threshold:
                        cluster.append(other_id)
                        assigned.add(other_id)
                
                clusters.append(cluster)
            
            logger.info(f"Clustered {len(observations)} observations into {len(clusters)} clusters")
            return clusters
            
        except Exception as e:
            logger.error(f"Clustering error: {e}")
            return []
        finally:
            session.close()
    
    def find_contradictions(
        self,
        query: str,
        k: int = 20
    ) -> List[Tuple[Dict, Dict, float]]:
        """
        Find potentially contradictory observations.
        
        Args:
            query: Query to find relevant observations
            k: Number of observations to consider
            
        Returns:
            List of (obs1, obs2, dissimilarity_score) tuples
        """
        session = get_session(self.engine)
        
        try:
            # Get relevant observations
            observations = self.semantic_search(query, k=k*2)
            
            if len(observations) < 2:
                return []
            
            # Look for contradictions: semantically similar but with opposing keywords
            contradiction_keywords = [
                ('yes', 'no'),
                ('true', 'false'),
                ('approved', 'denied'),
                ('confirmed', 'refuted'),
                ('guilty', 'innocent'),
                ('present', 'absent'),
            ]
            
            contradictions = []
            
            for i, obs1 in enumerate(observations):
                for obs2 in observations[i+1:]:
                    # Check if they're about similar topics but with opposing terms
                    text1 = obs1['context'].lower()
                    text2 = obs2['context'].lower()
                    
                    for word1, word2 in contradiction_keywords:
                        if (word1 in text1 and word2 in text2) or (word2 in text1 and word1 in text2):
                            # Calculate dissimilarity
                            dissimilarity = 1 - obs2['similarity']
                            contradictions.append((obs1, obs2, dissimilarity))
                            break
            
            logger.info(f"Found {len(contradictions)} potential contradictions")
            return contradictions
            
        except Exception as e:
            logger.error(f"Find contradictions error: {e}")
            return []
        finally:
            session.close()

