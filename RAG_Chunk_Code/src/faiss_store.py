"""
FAISS Vector Store (Free, Local)
Fast similarity search using Facebook AI Similarity Search
"""

import os
import pickle
from typing import List, Dict, Optional, Any
import numpy as np
from pathlib import Path

from .embedding import VectorStore


class FAISSStore(VectorStore):
    """FAISS vector store implementation (free, local, fast)."""
    
    def __init__(self, index_path: str = "./faiss_index", dimension: int = 384):
        """
        Initialize FAISS store.
        
        Args:
            index_path: Path to save/load FAISS index
            dimension: Embedding dimension (must match your embeddings)
        """
        try:
            import faiss
            self.faiss = faiss
        except ImportError:
            raise ImportError(
                "faiss-cpu or faiss-gpu required. Install with: pip install faiss-cpu"
            )
        
        self.index_path = Path(index_path)
        self.dimension = dimension
        
        # Create index directory if needed
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize FAISS index (Inner Product with normalized vectors = cosine similarity)
        # Using IndexFlatIP because we normalize embeddings
        self.index = self.faiss.IndexFlatIP(dimension)
        
        # Store metadata (maps index position to chunk metadata)
        self.metadata: List[Dict[str, Any]] = []
        
        # Load existing index if it exists
        self._load_index()
    
    def _load_index(self):
        """Load existing FAISS index and metadata if available."""
        index_file = self.index_path.with_suffix('.index')
        meta_file = self.index_path.with_suffix('.meta')
        
        if index_file.exists() and meta_file.exists():
            print(f"Loading existing FAISS index from {index_file}...")
            try:
                # Load FAISS index
                self.index = self.faiss.read_index(str(index_file))
                
                # Load metadata
                with open(meta_file, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                print(f"Loaded {len(self.metadata)} vectors from existing index")
            except Exception as e:
                print(f"Warning: Could not load existing index: {e}. Starting fresh.")
                self.index = self.faiss.IndexFlatIP(self.dimension)
                self.metadata = []
    
    def _save_index(self):
        """Save FAISS index and metadata to disk."""
        index_file = self.index_path.with_suffix('.index')
        meta_file = self.index_path.with_suffix('.meta')
        
        print(f"Saving FAISS index to {index_file}...")
        self.faiss.write_index(self.index, str(index_file))
        
        with open(meta_file, 'wb') as f:
            pickle.dump(self.metadata, f)
        
        print(f"Saved {len(self.metadata)} vectors")
    
    def upsert(self, vectors: List[Dict[str, Any]]):
        """
        Upsert vectors to FAISS index.
        
        Args:
            vectors: List of vector dictionaries with 'id', 'vector', and metadata
        """
        if not vectors:
            return
        
        # Extract embeddings and metadata
        embeddings = []
        new_metadata = []
        
        for vec in vectors:
            # Convert to numpy array
            embedding = np.array(vec['vector'], dtype=np.float32)
            
            # Ensure correct shape
            if embedding.ndim == 1:
                embedding = embedding.reshape(1, -1)
            
            # Verify dimension matches
            if embedding.shape[1] != self.dimension:
                raise ValueError(
                    f"Embedding dimension {embedding.shape[1]} doesn't match "
                    f"index dimension {self.dimension}"
                )
            
            embeddings.append(embedding)
            
            # Store metadata
            metadata = {
                'id': vec['id'],
                'text': vec['text'],
                'video_id': vec['video_id'],
                'start_seconds': vec['start_seconds'],
                'end_seconds': vec['end_seconds'],
                'speaker': vec.get('speaker', ''),
                'parent_id': vec.get('parent_id', ''),
                'publish_date': vec.get('publish_date', ''),
                'tier': vec.get('tier', ''),
                'title': vec.get('title', ''),
                'guest': vec.get('guest', ''),
            }
            
            # Handle topics list
            if 'topics' in vec:
                if isinstance(vec['topics'], list):
                    metadata['topics'] = ','.join(vec['topics'])
                else:
                    metadata['topics'] = vec['topics']
            
            new_metadata.append(metadata)
        
        # Concatenate embeddings
        embeddings_array = np.vstack(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings_array)
        
        # Append metadata
        self.metadata.extend(new_metadata)
        
        # Save index
        self._save_index()
        
        print(f"Added {len(vectors)} vectors to FAISS index (total: {len(self.metadata)})")
    
    def query(self, query_vector: List[float], top_k: int = 5,
             filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query FAISS index.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters (not fully implemented, filters after retrieval)
            
        Returns:
            List of results with metadata
        """
        if len(self.metadata) == 0:
            return []
        
        # Convert query to numpy array
        query_array = np.array([query_vector], dtype=np.float32)
        
        # Search
        distances, indices = self.index.search(query_array, min(top_k * 2, len(self.metadata)))
        
        # Format results
        formatted_results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.metadata):  # Invalid index
                continue
            
            metadata = self.metadata[idx]
            
            # Apply filters if provided
            if filters:
                match = True
                for key, value in filters.items():
                    if key not in metadata or metadata[key] != value:
                        match = False
                        break
                if not match:
                    continue
            
            # Convert distance to similarity score (for normalized vectors, distance is similarity)
            # FAISS IndexFlatIP returns inner product, which for normalized vectors = cosine similarity
            score = float(distances[0][i])
            
            formatted_results.append({
                'id': metadata['id'],
                'score': score,
                'text': metadata['text'],
                'video_id': metadata['video_id'],
                'start_seconds': metadata['start_seconds'],
                'end_seconds': metadata['end_seconds'],
                'speaker': metadata.get('speaker', ''),
                'parent_id': metadata.get('parent_id', ''),
                'tier': metadata.get('tier', ''),
                'title': metadata.get('title', ''),
                'guest': metadata.get('guest', ''),
                'topics': metadata.get('topics', '').split(',') if metadata.get('topics') else []
            })
            
            if len(formatted_results) >= top_k:
                break
        
        return formatted_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            'total_vectors': len(self.metadata),
            'dimension': self.dimension,
            'index_path': str(self.index_path)
        }
