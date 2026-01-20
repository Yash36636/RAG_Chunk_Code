"""
Two-Tier Embedding System
Implements core and longtail index separation for optimized retrieval.
"""

import uuid
from typing import List, Dict, Optional, Any, Tuple
from .chunking import ParentChildChunk
from .ingestion import VideoMetadata
from .chunk_classifier import ChunkClassifier, ChunkType
from .embedding_formatter import EmbeddingFormatter
from .embedding import EmbeddingGenerator, VectorStore


class TwoTierEmbeddingPipeline:
    """
    Two-tier embedding pipeline:
    - Core Index: content chunks (advice, frameworks, opinions)
    - Longtail Index: anecdote chunks (personal stories)
    """
    
    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        core_store: VectorStore,
        longtail_store: VectorStore,
        classifier: Optional[ChunkClassifier] = None,
        disable_two_tier: bool = True  # FIX 2: Temporarily disable two-tier
    ):
        """
        Initialize two-tier embedding pipeline.
        
        Args:
            embedding_generator: Embedding generator instance
            core_store: Vector store for core index
            longtail_store: Vector store for longtail index
            classifier: Optional chunk classifier (creates default if None)
            disable_two_tier: If True, put everything in core (temporary fix for recall)
        """
        self.embedding_generator = embedding_generator
        self.core_store = core_store
        self.longtail_store = longtail_store
        self.classifier = classifier or ChunkClassifier(relaxed_mode=True)
        self.disable_two_tier = disable_two_tier  # FIX 2
        
        # Store parent chunks for expansion during retrieval
        self.parent_store: Dict[str, str] = {}
    
    def index_chunks(
        self,
        child_chunks: List[ParentChildChunk],
        parent_chunks: List[ParentChildChunk],
        metadata: VideoMetadata,
        enriched_texts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Index child chunks into appropriate tier based on classification.
        
        Args:
            child_chunks: List of child chunks to index
            parent_chunks: List of parent chunks (stored for retrieval expansion)
            metadata: Video metadata
            enriched_texts: Optional enriched texts (not used for embedding, only for reference)
            
        Returns:
            Dictionary with indexing statistics
        """
        # Store parent chunks
        for parent_chunk in parent_chunks:
            if parent_chunk.id:
                self.parent_store[parent_chunk.id] = parent_chunk.text
        
        # Classify chunks
        classifications = self.classifier.classify_batch(child_chunks)
        stats = self.classifier.get_statistics(child_chunks, classifications)
        
        # FIX 2: TEMPORARILY DISABLE TWO-TIER
        # Put everything (except skipped) into core for now
        if self.disable_two_tier:
            core_chunks = []
            core_indices = []
            longtail_chunks = []
            longtail_indices = []
            
            for i, (chunk, cls) in enumerate(zip(child_chunks, classifications)):
                # Only skip if classifier says to skip
                if not self.classifier.should_embed(cls):
                    continue
                
                # Put everything in core (temporarily)
                core_chunks.append(chunk)
                core_indices.append(i)
        else:
            # Original two-tier logic (for later)
            core_chunks = []
            longtail_chunks = []
            core_indices = []
            longtail_indices = []
            
            for i, (chunk, cls) in enumerate(zip(child_chunks, classifications)):
                if cls == "content":
                    core_chunks.append(chunk)
                    core_indices.append(i)
                elif cls == "anecdote":
                    longtail_chunks.append(chunk)
                    longtail_indices.append(i)
        
        # Format texts for embedding (exclude timestamps, URLs, etc.)
        core_formatted = EmbeddingFormatter.format_batch(
            core_chunks, metadata, 
            enriched_texts=[enriched_texts[i] for i in core_indices] if enriched_texts else None
        )
        
        # FIX 2: Only process longtail if not disabled and has chunks
        if not self.disable_two_tier and longtail_chunks:
            longtail_formatted = EmbeddingFormatter.format_batch(
                longtail_chunks, metadata,
                enriched_texts=[enriched_texts[i] for i in longtail_indices] if enriched_texts else None
            )
        else:
            longtail_formatted = []
        
        # Generate embeddings
        print(f"Generating embeddings for {len(core_chunks)} core chunks...")
        # Check if embed_batch supports batch_size parameter (FreeEmbeddingGenerator does)
        if hasattr(self.embedding_generator, 'embed_batch'):
            # Try with batch_size if supported (FreeEmbeddingGenerator)
            try:
                core_embeddings = self.embedding_generator.embed_batch(
                    core_formatted, 
                    batch_size=64,
                    show_progress=True
                )
            except TypeError:
                # Fallback for EmbeddingGenerator (OpenAI) which doesn't support batch_size
                core_embeddings = self.embedding_generator.embed_batch(core_formatted)
        else:
            core_embeddings = [self.embedding_generator.embed(text) for text in core_formatted]
        
        # FIX 2: Only process longtail if not disabled and has chunks
        if not self.disable_two_tier and longtail_chunks:
            print(f"Generating embeddings for {len(longtail_chunks)} longtail chunks...")
            if hasattr(self.embedding_generator, 'embed_batch'):
                try:
                    longtail_embeddings = self.embedding_generator.embed_batch(
                        longtail_formatted,
                        batch_size=64,
                        show_progress=True
                    )
                except TypeError:
                    longtail_embeddings = self.embedding_generator.embed_batch(longtail_formatted)
            else:
                longtail_embeddings = [self.embedding_generator.embed(text) for text in longtail_formatted]
        else:
            longtail_embeddings = []
        
        # Prepare vectors for upsert
        core_vectors = self._prepare_vectors(
            core_chunks, core_embeddings, core_formatted, metadata, "core"
        )
        longtail_vectors = self._prepare_vectors(
            longtail_chunks, longtail_embeddings, longtail_formatted, metadata, "longtail"
        )
        
        # Upsert to respective stores
        if core_vectors:
            print(f"Upserting {len(core_vectors)} vectors to core index...")
            self.core_store.upsert(core_vectors)
        
        if longtail_vectors:
            print(f"Upserting {len(longtail_vectors)} vectors to longtail index...")
            self.longtail_store.upsert(longtail_vectors)
        
        return {
            "total_chunks": len(child_chunks),
            "core_chunks": len(core_chunks),
            "longtail_chunks": len(longtail_chunks),
            "skipped_chunks": stats["total"] - stats["embeddable"],
            "classification_stats": stats
        }
    
    def _prepare_vectors(
        self,
        chunks: List[ParentChildChunk],
        embeddings: List[List[float]],
        formatted_texts: List[str],
        metadata: VideoMetadata,
        tier: str
    ) -> List[Dict[str, Any]]:
        """Prepare vector records for upsert."""
        vectors = []
        
        for chunk, embedding, formatted_text in zip(chunks, embeddings, formatted_texts):
            vector_record = {
                'id': f"{tier}_{chunk.id}_{uuid.uuid4().hex[:8]}",  # Unique ID with tier prefix
                'vector': embedding,
                'text': chunk.text,  # Original text for display
                'formatted_text': formatted_text,  # What was actually embedded
                'video_id': metadata.video_id,
                'start_seconds': int(chunk.start_seconds),
                'end_seconds': int(chunk.end_seconds),
                'speaker': chunk.speaker or '',
                'parent_id': chunk.parent_id or '',
                'publish_date': metadata.publish_date,
                'tier': tier,  # "core" or "longtail"
                'title': metadata.title or '',
                'guest': metadata.guest or '',
                'topics': metadata.topics or []
            }
            vectors.append(vector_record)
        
        return vectors
    
    def get_parent_text(self, parent_id: str) -> Optional[str]:
        """Get parent chunk text by ID."""
        return self.parent_store.get(parent_id)
