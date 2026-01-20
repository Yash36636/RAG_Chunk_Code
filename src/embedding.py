"""
Embedding and Vector Storage Module
Handles embedding generation and vector database operations.
"""

import uuid
from typing import List, Dict, Optional, Any
from .chunking import ParentChildChunk
from .ingestion import VideoMetadata
import numpy as np


class VectorStore:
    """Abstract base class for vector storage."""
    
    def upsert(self, vectors: List[Dict[str, Any]]):
        """Upsert vectors to the store."""
        raise NotImplementedError
    
    def query(self, query_vector: List[float], top_k: int = 5, 
             filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query the vector store."""
        raise NotImplementedError


class EmbeddingGenerator:
    """Generates embeddings for text chunks."""
    
    def __init__(self, model_name: str = "text-embedding-3-large", 
                 dimensions: int = 1536, api_key: Optional[str] = None):
        """
        Initialize embedding generator.
        
        Args:
            model_name: OpenAI embedding model name
            dimensions: Embedding dimensions (1536 for large, 256 for small)
            api_key: OpenAI API key
        """
        self.model_name = model_name
        self.dimensions = dimensions
        self.api_key = api_key
        
        # Initialize OpenAI client if API key provided
        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("openai package required for embeddings")
        else:
            self.client = None
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized. Provide API key.")
        
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text,
                dimensions=self.dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {e}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embeddings.append(self.embed(text))
        return embeddings


class PineconeStore(VectorStore):
    """Pinecone vector store implementation."""
    
    def __init__(self, api_key: str, environment: str, index_name: str):
        """
        Initialize Pinecone store.
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment
            index_name: Index name
        """
        try:
            import pinecone
            self.pinecone = pinecone
        except ImportError:
            raise ImportError("pinecone-client package required")
        
        # Initialize Pinecone
        self.pinecone.init(api_key=api_key, environment=environment)
        self.index = self.pinecone.Index(index_name)
        self.index_name = index_name
    
    def upsert(self, vectors: List[Dict[str, Any]]):
        """Upsert vectors to Pinecone."""
        # Format vectors for Pinecone
        pinecone_vectors = []
        for vec in vectors:
            metadata = {
                'text': vec['text'],
                'video_id': vec['video_id'],
                'start_seconds': vec['start_seconds'],
                'end_seconds': vec['end_seconds'],
                'speaker': vec.get('speaker', ''),
                'parent_id': vec.get('parent_id', ''),
                'publish_date': vec.get('publish_date', ''),
                'chapter_title': vec.get('chapter_title', '')
            }
            
            # Add new metadata fields for two-tier system
            if 'tier' in vec:
                metadata['tier'] = vec['tier']
            if 'title' in vec:
                metadata['title'] = vec['title']
            if 'guest' in vec:
                metadata['guest'] = vec['guest']
            if 'topics' in vec:
                metadata['topics'] = ','.join(vec['topics']) if isinstance(vec['topics'], list) else vec['topics']
            
            pinecone_vectors.append({
                'id': vec['id'],
                'values': vec['vector'],
                'metadata': metadata
            })
        
        self.index.upsert(vectors=pinecone_vectors)
    
    def query(self, query_vector: List[float], top_k: int = 5,
             filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query Pinecone index."""
        query_filter = {}
        if filters:
            query_filter = filters
        
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=query_filter if query_filter else None
        )
        
        # Format results
        formatted_results = []
        for match in results['matches']:
            metadata = match['metadata']
            formatted_results.append({
                'id': match['id'],
                'score': match['score'],
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
        
        return formatted_results


class EmbeddingPipeline:
    """Pipeline for embedding and indexing chunks."""
    
    def __init__(self, embedding_generator: EmbeddingGenerator, 
                 vector_store: VectorStore, parent_store: Optional[Dict[str, str]] = None):
        """
        Initialize embedding pipeline.
        
        Args:
            embedding_generator: Embedding generator instance
            vector_store: Vector store instance
            parent_store: Optional dict to store parent chunk texts (keyed by parent_id)
        """
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store
        self.parent_store = parent_store or {}
    
    def index_chunks(self, child_chunks: List[ParentChildChunk],
                    parent_chunks: List[ParentChildChunk],
                    meta: VideoMetadata, enriched_texts: List[str]):
        """
        Index child chunks with embeddings.
        
        Args:
            child_chunks: List of child chunks to index
            parent_chunks: List of parent chunks
            enriched_texts: List of enriched texts (one per child chunk)
            meta: Video metadata
        """
        # Store parent chunks
        for parent_chunk in parent_chunks:
            if parent_chunk.id:
                self.parent_store[parent_chunk.id] = parent_chunk.text
        
        # Generate embeddings for child chunks
        vectors_to_upsert = []
        
        for idx, (child_chunk, enriched_text) in enumerate(zip(child_chunks, enriched_texts)):
            # Generate embedding
            embedding = self.embedding_generator.embed(enriched_text)
            
            # Create vector record
            vector_record = {
                'id': str(uuid.uuid4()),
                'vector': embedding,
                'text': child_chunk.text,  # Original text for display
                'video_id': meta.video_id,
                'start_seconds': int(child_chunk.start_seconds),
                'end_seconds': int(child_chunk.end_seconds),
                'speaker': child_chunk.speaker or '',
                'parent_id': child_chunk.parent_id or '',
                'publish_date': meta.publish_date,
                'chapter_title': ''  # Can be populated from chapter parsing
            }
            
            vectors_to_upsert.append(vector_record)
        
        # Upsert to vector store
        self.vector_store.upsert(vectors_to_upsert)
    
    def create_deep_link(self, video_id: str, start_seconds: int, 
                        lead_in: int = 5) -> str:
        """
        Create YouTube deep link with lead-in.
        
        Args:
            video_id: YouTube video ID
            start_seconds: Start time in seconds
            lead_in: Seconds to subtract for lead-in
            
        Returns:
            YouTube URL with timestamp
        """
        adjusted_start = max(0, start_seconds - lead_in)
        return f"https://www.youtube.com/watch?v={video_id}&t={adjusted_start}s"
