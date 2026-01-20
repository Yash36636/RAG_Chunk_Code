"""
Chunk Classifier Module
Lightweight rule-based classifier to categorize child chunks before embedding.
"""

from typing import List, Literal
from .chunking import ParentChildChunk


ChunkType = Literal["content", "anecdote", "meta", "sponsor", "banter"]


class ChunkClassifier:
    """
    Rule-based classifier for child chunks.
    
    Classifies chunks into:
    - content: advice, frameworks, opinions (EMBED)
    - anecdote: personal stories (EMBED)
    - meta: podcast transitions (SKIP)
    - sponsor: ads, promos (SKIP)
    - banter: jokes, filler (SKIP)
    """
    
    def __init__(self, min_content_words: int = 25, relaxed_mode: bool = True):
        """
        Initialize classifier.
        
        Args:
            min_content_words: Minimum words to be considered content (not banter)
            relaxed_mode: If True, use relaxed filtering (embed ~40-60% instead of ~10%)
        """
        self.min_content_words = min_content_words
        self.relaxed_mode = relaxed_mode
        
        # FIX 1: RELAXED - Only hard sponsor/ad filters
        # Only skip if clearly an ad/sponsor
        self.sponsor_keywords = [
            "sponsor", "sponsored", "brought to you by",
            "use code", "sign up at", "visit", "dot com",
            "free trial", "limited time"
        ]
        
        # FIX 1: RELAXED - Only intro/outro boilerplate
        self.meta_keywords = [
            "welcome to the podcast",
            "thanks for listening",
            "subscribe on",
            "leave a review",
            "see you next episode"
        ]
        
        # Anecdote indicators (personal stories)
        self.anecdote_indicators = [
            "i remember", "when i", "one time", "years ago", "back when",
            "story", "told me", "happened", "experience", "once"
        ]
        
        # Signal words that indicate useful content (even if short)
        self.signal_words = [
            "prioritize", "decide", "approach", "framework", "tradeoff",
            "strategy", "method", "process", "technique", "principle",
            "how to", "what is", "why", "because", "should", "recommend"
        ]
    
    def should_skip_chunk(self, text: str) -> bool:
        """
        FIX 1: RELAXED FILTERING
        Only skip chunks that are clearly junk.
        
        Args:
            text: Chunk text to check
            
        Returns:
            True if chunk should be skipped, False if it should be embedded
        """
        t = text.lower().strip()
        word_count = len(text.split())
        
        # 1. Hard sponsor / ad filters (ONLY skip if clearly an ad)
        for keyword in self.sponsor_keywords:
            if keyword in t:
                return True
        
        # 2. Intro / outro boilerplate
        for keyword in self.meta_keywords:
            if keyword in t:
                return True
        
        # 3. Pure filler (VERY short + no signal words)
        if word_count < self.min_content_words:
            # Check if it has signal words - if yes, keep it
            has_signal = any(signal in t for signal in self.signal_words)
            if not has_signal:
                return True
        
        # Everything else should be embedded
        return False
    
    def classify(self, chunk: ParentChildChunk) -> ChunkType:
        """
        Classify a single chunk.
        FIX 1: RELAXED - Only skip obvious junk, embed everything else.
        
        Args:
            chunk: Child chunk to classify
            
        Returns:
            Chunk type classification
        """
        text_lower = chunk.text.lower()
        word_count = len(chunk.text.split())
        
        # FIX 1: Use relaxed should_skip logic
        if self.should_skip_chunk(chunk.text):
            # Determine skip reason for stats
            for keyword in self.sponsor_keywords:
                if keyword in text_lower:
                    return "sponsor"
            for keyword in self.meta_keywords:
                if keyword in text_lower:
                    return "meta"
            # Must be too short without signal words
            return "banter"
        
        # Check for anecdote indicators (but still embed them)
        anecdote_score = sum(1 for indicator in self.anecdote_indicators 
                           if indicator in text_lower)
        if anecdote_score >= 2:  # Multiple indicators = likely anecdote
            return "anecdote"
        
        # Default: content (advice, frameworks, opinions)
        # FIX 1: Now most chunks will be classified as content
        return "content"
    
    def classify_batch(self, chunks: List[ParentChildChunk]) -> List[ChunkType]:
        """
        Classify multiple chunks.
        
        Args:
            chunks: List of child chunks
            
        Returns:
            List of classifications (same order as chunks)
        """
        return [self.classify(chunk) for chunk in chunks]
    
    def should_embed(self, chunk_type: ChunkType) -> bool:
        """
        Determine if a chunk type should be embedded.
        
        Args:
            chunk_type: Classification result
            
        Returns:
            True if chunk should be embedded, False otherwise
        """
        return chunk_type in ["content", "anecdote"]
    
    def get_index_tier(self, chunk_type: ChunkType) -> Literal["core", "longtail"]:
        """
        Determine which index tier a chunk belongs to.
        
        Args:
            chunk_type: Classification result
            
        Returns:
            "core" for content chunks, "longtail" for anecdotes
        """
        if chunk_type == "content":
            return "core"
        elif chunk_type == "anecdote":
            return "longtail"
        else:
            # Should not be called for non-embeddable types
            raise ValueError(f"Cannot determine index tier for non-embeddable type: {chunk_type}")
    
    def filter_embeddable(self, chunks: List[ParentChildChunk], 
                         classifications: List[ChunkType]) -> List[ParentChildChunk]:
        """
        Filter chunks to only those that should be embedded.
        
        Args:
            chunks: List of all child chunks
            classifications: List of classifications (same order)
            
        Returns:
            Filtered list of chunks to embed
        """
        return [chunk for chunk, cls in zip(chunks, classifications) 
                if self.should_embed(cls)]
    
    def get_statistics(self, chunks: List[ParentChildChunk], 
                      classifications: List[ChunkType]) -> dict:
        """
        Get classification statistics.
        
        Args:
            chunks: List of chunks
            classifications: List of classifications
            
        Returns:
            Dictionary with counts by type
        """
        stats = {
            "total": len(chunks),
            "content": 0,
            "anecdote": 0,
            "meta": 0,
            "sponsor": 0,
            "banter": 0,
            "embeddable": 0
        }
        
        for cls in classifications:
            stats[cls] = stats.get(cls, 0) + 1
            if self.should_embed(cls):
                stats["embeddable"] += 1
        
        return stats
