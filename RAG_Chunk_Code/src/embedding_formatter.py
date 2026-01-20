"""
Embedding Input Formatter
Formats chunk text for embedding, excluding non-semantic elements.
"""

from typing import Optional
from .chunking import ParentChildChunk
from .ingestion import VideoMetadata


class EmbeddingFormatter:
    """
    Formats text for embedding by including only semantic content.
    
    Excludes:
    - Timestamps
    - YouTube URLs
    - Episode descriptions
    - Parent text (already excluded - we use child.text)
    
    Includes:
    - Video title
    - Guest name
    - Topics
    - Child chunk text
    """
    
    @staticmethod
    def format_for_embedding(
        chunk: ParentChildChunk,
        metadata: VideoMetadata,
        include_enriched_context: bool = False,
        enriched_text: Optional[str] = None
    ) -> str:
        """
        Format chunk text for embedding.
        
        Args:
            chunk: Child chunk to embed
            metadata: Video metadata
            include_enriched_context: Whether to use enriched text (default: False, use child.text)
            enriched_text: Optional enriched text (if include_enriched_context=True)
            
        Returns:
            Formatted text ready for embedding
        """
        # Build context header
        parts = []
        
        # Video title
        if metadata.title:
            parts.append(f"Video: {metadata.title}")
        
        # Guest name
        if metadata.guest:
            parts.append(f"Guest: {metadata.guest}")
        
        # Topics
        if metadata.topics:
            topics_str = ", ".join(metadata.topics)
            parts.append(f"Topics: {topics_str}")
        
        # Main text content
        # Use enriched_text only if explicitly requested (for future use)
        # For now, use child.text directly (enriched_text is for retrieval context, not embedding)
        main_text = enriched_text if (include_enriched_context and enriched_text) else chunk.text
        
        # Remove any URLs that might have leaked in
        main_text = EmbeddingFormatter._remove_urls(main_text)
        
        # Remove timestamps (format: HH:MM:SS or similar)
        main_text = EmbeddingFormatter._remove_timestamps(main_text)
        
        parts.append(f"Text: {main_text}")
        
        return "\n".join(parts)
    
    @staticmethod
    def _remove_urls(text: str) -> str:
        """Remove URLs from text."""
        import re
        # Remove http/https URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove www. URLs
        text = re.sub(r'www\.\S+', '', text)
        return text.strip()
    
    @staticmethod
    def _remove_timestamps(text: str) -> str:
        """Remove timestamp patterns from text."""
        import re
        # Remove patterns like (00:12:34) or [00:12:34] or 00:12:34
        text = re.sub(r'[\[\(]?\d{1,2}:\d{2}:\d{2}[\]\)]?', '', text)
        # Remove patterns like 00:12 or 12:34
        text = re.sub(r'\d{1,2}:\d{2}(?!\d)', '', text)
        return text.strip()
    
    @staticmethod
    def format_batch(
        chunks: list[ParentChildChunk],
        metadata: VideoMetadata,
        enriched_texts: Optional[list[str]] = None
    ) -> list[str]:
        """
        Format multiple chunks for embedding.
        
        Args:
            chunks: List of child chunks
            metadata: Video metadata (same for all chunks)
            enriched_texts: Optional list of enriched texts (one per chunk)
            
        Returns:
            List of formatted texts ready for embedding
        """
        if enriched_texts and len(enriched_texts) != len(chunks):
            raise ValueError("enriched_texts length must match chunks length")
        
        formatted = []
        for i, chunk in enumerate(chunks):
            enriched = enriched_texts[i] if enriched_texts else None
            formatted_text = EmbeddingFormatter.format_for_embedding(
                chunk=chunk,
                metadata=metadata,
                include_enriched_context=False,  # Use child.text, not enriched
                enriched_text=enriched
            )
            formatted.append(formatted_text)
        
        return formatted
