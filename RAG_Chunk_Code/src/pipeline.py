"""
Main Pipeline Orchestrator
Ties all components together into a complete processing pipeline.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path

from .ingestion import FileIngester, IngestedVideo
from .parser import TranscriptParser
from .cleaning import TextCleaner
from .chunking import HierarchicalChunker
from .embedding import EmbeddingGenerator, EmbeddingPipeline, VectorStore


class VideoRAGPipeline:
    """Complete pipeline for processing video transcripts."""
    
    def __init__(self, 
                 transcripts_dir: str = "transcripts",
                 embedding_api_key: Optional[str] = None,
                 vector_store: Optional[VectorStore] = None,
                 parent_window_tokens: int = 2000,
                 child_window_tokens: int = 250):
        """
        Initialize the complete pipeline.
        
        Args:
            transcripts_dir: Directory containing transcript files
            embedding_api_key: OpenAI API key for embeddings
            vector_store: Vector store instance (optional)
            parent_window_tokens: Size of parent chunks
            child_window_tokens: Size of child chunks
        """
        # Initialize components
        self.ingester = FileIngester(transcripts_dir)
        self.parser = TranscriptParser()
        self.cleaner = TextCleaner()
        self.chunker = HierarchicalChunker(
            parent_window_tokens=parent_window_tokens,
            child_window_tokens=child_window_tokens
        )
        
        # Initialize embedding components
        if embedding_api_key:
            self.embedding_generator = EmbeddingGenerator(
                api_key=embedding_api_key,
                dimensions=1536
            )
            self.embedding_pipeline = EmbeddingPipeline(
                embedding_generator=self.embedding_generator,
                vector_store=vector_store or self._create_default_store()
            )
        else:
            self.embedding_generator = None
            self.embedding_pipeline = None
    
    def _create_default_store(self) -> VectorStore:
        """Create a default in-memory store for testing."""
        # In production, you'd create a real vector store here
        # For now, return None and handle it gracefully
        return None
    
    def process_file(self, file_path: str, 
                    metadata_override: Optional[Dict[str, Any]] = None,
                    index: bool = True) -> Dict[str, Any]:
        """
        Process a single transcript file.
        
        Args:
            file_path: Path to transcript file
            metadata_override: Optional metadata overrides
            index: Whether to index the processed chunks
            
        Returns:
            Dictionary with processing results
        """
        # Step 1: Ingestion
        print(f"Ingesting transcript from {file_path}...")
        ingested = self.ingester.ingest_from_file(file_path, metadata_override=metadata_override)
        
        # Step 2: Parsing
        print("Parsing transcript format...")
        segments = self.parser.parse_speaker_format(ingested.raw_text)
        
        # Validate temporal ordering
        violations = self.parser.validate_temporal_ordering(segments)
        if violations:
            print(f"Warning: Found {len(violations)} temporal ordering violations")
        
        # Step 3: Cleaning
        print("Cleaning transcript text...")
        cleaned_segments = self.cleaner.clean_segments(segments)
        
        # Step 4: Chunking
        print("Creating hierarchical chunks...")
        parent_chunks, child_chunks = self.chunker.chunk(cleaned_segments, ingested.meta)
        
        print(f"Created {len(parent_chunks)} parent chunks and {len(child_chunks)} child chunks")
        
        # Step 5: Contextual Enrichment
        # FIX 4: Enrichment happens exactly ONCE here in pipeline
        print("Enriching chunks with context...")
        parent_lookup = {p.id: p for p in parent_chunks}
        enriched_texts = []
        
        for child_chunk in child_chunks:
            parent_chunk = parent_lookup.get(child_chunk.parent_id)
            if parent_chunk:
                enriched_text = self.chunker.enrich_with_context(
                    child_chunk, parent_chunk, ingested.meta
                )
                # FIX 4: Hard assertion - fail fast if enrichment is wrong
                assert child_chunk.text in enriched_text, (
                    f"Enriched text for child {child_chunk.id} doesn't contain chunk text. "
                    f"Child text: {child_chunk.text[:100]}... "
                    f"Enriched text: {enriched_text[:100]}..."
                )
            else:
                raise ValueError(f"No parent found for child {child_chunk.id} with parent_id {child_chunk.parent_id}")
            enriched_texts.append(enriched_text)
        
        # Step 6: Indexing (if enabled and embedding generator available)
        if index and self.embedding_pipeline:
            print("Indexing chunks...")
            self.embedding_pipeline.index_chunks(
                child_chunks, parent_chunks, ingested.meta, enriched_texts
            )
            print("Indexing complete!")
        
        # Return results
        return {
            'ingested': ingested,
            'segments': cleaned_segments,
            'parent_chunks': parent_chunks,
            'child_chunks': child_chunks,
            'enriched_texts': enriched_texts,
            'metadata': ingested.meta
        }
    
    def process_directory(self, directory: Optional[str] = None,
                         index: bool = True) -> List[Dict[str, Any]]:
        """
        Process all transcript files in a directory.
        
        Args:
            directory: Directory path (uses default if not provided)
            index: Whether to index the processed chunks
            
        Returns:
            List of processing results
        """
        results = []
        
        # Get all transcript files
        dir_path = Path(directory) if directory else Path(self.ingester.transcripts_dir)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
        
        transcript_files = list(dir_path.glob("*.txt")) + list(dir_path.glob("*.md"))
        
        for file_path in transcript_files:
            try:
                result = self.process_file(str(file_path), index=index)
                results.append(result)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        return results
