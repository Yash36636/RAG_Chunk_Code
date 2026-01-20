"""
Text Normalization and Cleaning Module
Removes artifacts, reconstructs sentences, and optimizes signal-to-noise ratio.
"""

import re
from typing import List
from .ingestion import Segment


class TextCleaner:
    """Cleans transcript text by removing artifacts and reconstructing sentences."""
    
    def __init__(self):
        # Pattern for common caption artifacts
        self.artifact_patterns = [
            r'\[(?:inaudible|crosstalk|music|applause|laughter|background).*?\]',
            r'\(.*?inaudible.*?\)',
            r'\[.*?\d{2}:\d{2}:\d{2}.*?\]',  # Timestamp artifacts
        ]
        
        # Pattern for general brackets (be more careful)
        self.bracket_pattern = re.compile(r'\[.*?\]|\(.*?\)')
    
    def remove_artifacts(self, text: str) -> str:
        """
        Remove non-semantic artifacts from transcript text.
        
        Args:
            text: Raw transcript text
            
        Returns:
            Cleaned text
        """
        cleaned = text
        
        # Remove specific artifact patterns
        for pattern in self.artifact_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def reconstruct_sentences(self, text: str) -> str:
        """
        Reconstruct sentences from line-broken text.
        Buffers lines until terminal punctuation is found.
        
        Args:
            text: Text with potential line breaks
            
        Returns:
            Text with reconstructed sentences
        """
        lines = text.split('\n')
        reconstructed = []
        buffer = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            buffer.append(line)
            
            # Check if line ends with terminal punctuation
            if re.search(r'[.!?]\s*$', line):
                # Join buffer and add to reconstructed
                sentence = ' '.join(buffer)
                reconstructed.append(sentence)
                buffer = []
        
        # Add any remaining buffer
        if buffer:
            reconstructed.append(' '.join(buffer))
        
        return ' '.join(reconstructed)
    
    def clean_segment(self, segment: Segment) -> Segment:
        """
        Clean a single segment.
        
        Args:
            segment: Segment to clean
            
        Returns:
            Cleaned segment
        """
        # Remove artifacts
        cleaned_text = self.remove_artifacts(segment.text)
        
        # Reconstruct sentences
        cleaned_text = self.reconstruct_sentences(cleaned_text)
        
        # Create new segment with cleaned text
        cleaned_segment = Segment(
            text=cleaned_text,
            start=segment.start,
            duration=segment.duration,
            speaker=segment.speaker
        )
        
        return cleaned_segment
    
    def clean_segments(self, segments: List[Segment]) -> List[Segment]:
        """
        Clean a list of segments.
        
        Args:
            segments: List of segments to clean
            
        Returns:
            List of cleaned segments
        """
        return [self.clean_segment(seg) for seg in segments]
