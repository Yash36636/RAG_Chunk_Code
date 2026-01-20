"""
Hierarchical Chunking Module
Implements Parent-Child chunking strategy with contextual enrichment.
"""

import tiktoken
from typing import List, Dict, Optional, Tuple
from .ingestion import Segment, VideoMetadata
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class ParentChildChunk:
    """Represents a chunk in the hierarchical structure."""
    
    def __init__(self, text: str, start_seconds: float, end_seconds: float,
                 speaker: Optional[str] = None, parent_id: Optional[str] = None,
                 chunk_type: str = "child"):
        self.text = text
        self.start_seconds = start_seconds
        self.end_seconds = end_seconds
        self.speaker = speaker
        self.parent_id = parent_id
        self.chunk_type = chunk_type  # "parent" or "child"
        self.id = None  # Will be set during indexing
        # FIX 2: Track segment indices for index-based parent-child mapping
        self.segment_indices: List[int] = []


class HierarchicalChunker:
    """Implements hierarchical parent-child chunking strategy."""
    
    def __init__(self, parent_window_tokens: int = 2000, child_window_tokens: int = 250,
                 child_overlap_tokens: int = 50, embedding_model=None):
        """
        Initialize chunker.
        
        Args:
            parent_window_tokens: Size of parent chunks in tokens (~5-7 minutes)
            child_window_tokens: Size of child chunks in tokens (~30 seconds)
            child_overlap_tokens: Overlap between child chunks
            embedding_model: Optional embedding model for semantic chunking
        """
        self.parent_window_tokens = parent_window_tokens
        self.child_window_tokens = child_window_tokens
        self.child_overlap_tokens = child_overlap_tokens
        self.embedding_model = embedding_model
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
    
    def create_parent_chunks(self, segments: List[Segment], 
                            meta: VideoMetadata) -> List[ParentChildChunk]:
        """
        Create parent chunks from segments.
        Parent chunks are large windows (~5-7 minutes) that capture full narrative arcs.
        
        FIX 2: Track segment indices instead of relying on timestamps.
        
        Args:
            segments: List of cleaned segments
            meta: Video metadata
            
        Returns:
            List of parent chunks with segment_indices populated
        """
        parent_chunks = []
        current_text = []
        current_indices = []
        current_start = segments[0].start if segments else 0.0
        current_tokens = 0
        
        for i, segment in enumerate(segments):
            tokens = self.count_tokens(segment.text)
            
            if current_tokens + tokens > self.parent_window_tokens and current_text:
                # Create parent chunk
                parent_text = " ".join(current_text)
                parent_end = segment.start  # End before current segment
                
                parent_chunk = ParentChildChunk(
                    text=parent_text,
                    start_seconds=current_start,
                    end_seconds=parent_end,
                    speaker=None,  # Parent may have multiple speakers
                    chunk_type="parent"
                )
                parent_chunk.segment_indices = current_indices.copy()
                parent_chunks.append(parent_chunk)
                
                # Start new parent
                current_text = [segment.text]
                current_indices = [i]
                current_start = segment.start
                current_tokens = tokens
            else:
                current_text.append(segment.text)
                current_indices.append(i)
                current_tokens += tokens
        
        # Add final parent chunk
        if current_text:
            last_seg = segments[current_indices[-1]]
            parent_text = " ".join(current_text)
            parent_end = last_seg.start + last_seg.duration
            
            parent_chunk = ParentChildChunk(
                text=parent_text,
                start_seconds=current_start,
                end_seconds=parent_end,
                chunk_type="parent"
            )
            parent_chunk.segment_indices = current_indices
            parent_chunks.append(parent_chunk)
        
        return parent_chunks
    
    def create_child_chunks(self, parent_chunk: ParentChildChunk, 
                           parent_id: str, segments: List[Segment]) -> List[ParentChildChunk]:
        """
        Create child chunks from a parent chunk.
        Child chunks are small, overlapping windows for granular retrieval.
        
        FIX 3: Use parent.segment_indices instead of timestamp matching.
        OPTIMIZED: Direct token decode (more efficient than character position calculation).
        
        Args:
            parent_chunk: Parent chunk to subdivide
            parent_id: ID of the parent chunk
            segments: Original segments (for precise timing)
            
        Returns:
            List of child chunks
        """
        child_chunks = []
        
        # FIX 3: Use segment indices instead of timestamp matching
        parent_segments = [segments[i] for i in parent_chunk.segment_indices]
        parent_text = " ".join(seg.text for seg in parent_segments)
        
        if not parent_segments:
            return child_chunks
        
        # OPTIMIZATION: Direct token decode (like reference implementation)
        tokens = self.tokenizer.encode(parent_text) if self.tokenizer else None
        if not tokens:
            # Fallback for no tokenizer - use character-based approximation
            parent_tokens = self.count_tokens(parent_text)
            step = self.child_window_tokens - self.child_overlap_tokens
            pos = 0
            
            while pos < parent_tokens:
                end = min(pos + self.child_window_tokens, parent_tokens)
                char_start = int((pos / parent_tokens) * len(parent_text))
                char_end = int((end / parent_tokens) * len(parent_text))
                text = parent_text[char_start:char_end]
                
                child_chunk = ParentChildChunk(
                    text=text,
                    start_seconds=parent_chunk.start_seconds,
                    end_seconds=parent_chunk.end_seconds,
                    speaker=None,
                    parent_id=parent_id,
                    chunk_type="child"
                )
                child_chunks.append(child_chunk)
                
                pos += step
                if end >= parent_tokens:
                    break
            
            return child_chunks
        
        # OPTIMIZED PATH: Direct token decode
        step = self.child_window_tokens - self.child_overlap_tokens
        pos = 0
        
        while pos < len(tokens):
            end = min(pos + self.child_window_tokens, len(tokens))
            
            # OPTIMIZATION: Direct decode (more efficient)
            chunk_text = self.tokenizer.decode(tokens[pos:end])
            
            child_chunk = ParentChildChunk(
                text=chunk_text,
                start_seconds=parent_chunk.start_seconds,
                end_seconds=parent_chunk.end_seconds,
                speaker=None,
                parent_id=parent_id,
                chunk_type="child"
            )
            
            child_chunks.append(child_chunk)
            
            pos += step
            if end >= len(tokens):
                break
        
        return child_chunks
    
    def _estimate_timestamp(self, start: float, end: float, ratio: float) -> float:
        """Estimate timestamp based on position ratio."""
        return start + (end - start) * ratio
    
    def _get_dominant_speaker(self, segments: List[Segment], 
                              start: float, end: float) -> Optional[str]:
        """Get the most common speaker in a time range."""
        speakers = [
            seg.speaker for seg in segments
            if seg.start >= start and seg.start < end and seg.speaker
        ]
        
        if not speakers:
            return None
        
        # Return most common speaker
        return max(set(speakers), key=speakers.count)
    
    def enrich_with_context(self, child_chunk: ParentChildChunk,
                           parent_chunk: ParentChildChunk,
                           meta: VideoMetadata) -> str:
        """
        Enrich child chunk with contextual information.
        Creates embedding text with video context, speaker, and topic.
        
        Args:
            child_chunk: Child chunk to enrich
            parent_chunk: Parent chunk for context
            meta: Video metadata
            
        Returns:
            Enriched text for embedding
        """
        # Generate context summary (simplified - in production, use LLM)
        context_parts = []
        
        if meta.title:
            context_parts.append(f"Video: {meta.title}")
        
        if child_chunk.speaker:
            context_parts.append(f"Speaker: {child_chunk.speaker}")
        
        if meta.guest:
            context_parts.append(f"Guest: {meta.guest}")
        
        if meta.topics:
            topics_str = ", ".join(meta.topics[:3])  # Top 3 topics
            context_parts.append(f"Topics: {topics_str}")
        
        context = ". ".join(context_parts)
        
        # Create enriched text
        enriched = f"{context}. Text: {child_chunk.text}"
        
        return enriched
    
    def chunk(self, segments: List[Segment], meta: VideoMetadata) -> Tuple[List[ParentChildChunk], List[ParentChildChunk]]:
        """
        Main chunking method.
        
        FIX 5: IDs assigned ONLY here - single source of truth.
        
        Args:
            segments: List of cleaned segments
            meta: Video metadata
            
        Returns:
            Tuple of (parent_chunks, child_chunks)
        """
        # Create parent chunks
        parent_chunks = self.create_parent_chunks(segments, meta)
        
        # Create child chunks for each parent
        all_child_chunks = []
        child_idx = 0  # FIX 5: Sequential child ID counter
        
        for idx, parent_chunk in enumerate(parent_chunks):
            parent_id = f"parent_{idx}"
            parent_chunk.id = parent_id  # FIX 5: Assign ID here only
            
            child_chunks = self.create_child_chunks(parent_chunk, parent_id, segments)
            # FIX 5: Assign sequential IDs to child chunks
            for child_chunk in child_chunks:
                child_chunk.id = f"child_{child_idx}"
                child_idx += 1
            all_child_chunks.extend(child_chunks)
        
        # FIX 6: Safety check - ensure no cross-parent contamination
        parent_lookup = {p.id: p for p in parent_chunks}
        for child in all_child_chunks:
            parent = parent_lookup.get(child.parent_id)
            if parent is None:
                raise ValueError(f"Child {child.id} has invalid parent_id: {child.parent_id}")
            if child.text not in parent.text:
                raise ValueError(
                    f"Child {child.id} text not found in parent {parent.id} text. "
                    f"This indicates cross-parent contamination."
                )
        
        return parent_chunks, all_child_chunks
