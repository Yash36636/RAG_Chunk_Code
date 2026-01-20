"""
Text Parsing Module
Handles parsing of transcript formats, speaker extraction, and timestamp conversion.
"""

import re
from typing import List, Optional, Tuple
from .ingestion import Segment


class TranscriptParser:
    """Parses various transcript formats into structured Segment objects."""
    
    def __init__(self):
        # Pattern for "Speaker Name (HH:MM:SS): Text" format
        self.speaker_pattern = re.compile(
            r'^(.*?)\s+\((\d{1,2}):(\d{2}):(\d{2})\):\s*(.*)$',
            re.MULTILINE
        )
        # Pattern for "Speaker Name:" format (without timestamps)
        self.speaker_simple_pattern = re.compile(
            r'^([A-Z][^:]+):\s*(.*)$'
        )
    
    def parse_timestamp(self, timestamp_str: str) -> float:
        """
        Convert HH:MM:SS format to seconds.
        
        Args:
            timestamp_str: Time string in format "HH:MM:SS" or "H:MM:SS"
            
        Returns:
            Total seconds as float
        """
        parts = timestamp_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}")
    
    def parse_speaker_format(self, text: str) -> List[Segment]:
        """
        Parse transcript in "Speaker Name (HH:MM:SS): Text" format or "Speaker Name:" format.
        
        Supports two formats:
        1. "Ada Chen Rekhi (00:00:00): It's a terrible outcome..."
        2. "Adriel Frederick: There are probably..."
        
        Args:
            text: Raw transcript text
            
        Returns:
            List of Segment objects with speaker and timestamp information
        """
        segments = []
        lines = text.split('\n')
        
        current_speaker = None
        current_start = 0.0
        current_text_parts = []
        estimated_time = 0.0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip markdown headers
            if line.startswith('#'):
                continue
            
            # Try to match timestamp format first
            match = self.speaker_pattern.match(line)
            
            if match:
                # Save previous segment if exists
                if current_text_parts and current_speaker is not None:
                    segment = Segment(
                        text=' '.join(current_text_parts),
                        start=current_start,
                        duration=0.0,  # Will be calculated later
                        speaker=current_speaker
                    )
                    segments.append(segment)
                
                # Extract new speaker info
                speaker_name = match.group(1).strip()
                hours = int(match.group(2))
                minutes = int(match.group(3))
                seconds = int(match.group(4))
                text_content = match.group(5).strip()
                
                current_speaker = speaker_name
                current_start = hours * 3600 + minutes * 60 + seconds
                estimated_time = current_start
                current_text_parts = [text_content] if text_content else []
                
            else:
                # Try simple "Speaker Name:" format
                simple_match = self.speaker_simple_pattern.match(line)
                if simple_match:
                    # Save previous segment if exists
                    if current_text_parts and current_speaker is not None:
                        segment = Segment(
                            text=' '.join(current_text_parts),
                            start=current_start,
                            duration=0.0,
                            speaker=current_speaker
                        )
                        segments.append(segment)
                        # Update estimated time for next segment
                        word_count = len(segment.text.split())
                        estimated_time += max(word_count / 2.5, 5.0)
                    
                    # Extract new speaker info
                    speaker_name = simple_match.group(1).strip()
                    text_content = simple_match.group(2).strip()
                    
                    current_speaker = speaker_name
                    current_start = estimated_time  # Use estimated time
                    # Start with text on same line if present, otherwise wait for next line
                    current_text_parts = [text_content] if text_content else []
                else:
                    # Continuation of current speaker's text
                    if current_speaker is not None:
                        current_text_parts.append(line)
                    # If no current speaker and line doesn't start with #, it might be orphaned text
                    elif not line.startswith('#'):
                        # Skip orphaned lines (not headers, not speaker lines)
                        pass
        
        # Don't forget the last segment
        if current_text_parts and current_speaker is not None:
            segment = Segment(
                text=' '.join(current_text_parts),
                start=current_start,
                duration=0.0,
                speaker=current_speaker
            )
            segments.append(segment)
        
        # Calculate durations
        if segments:
            for i in range(len(segments) - 1):
                # Estimate duration based on text length
                word_count = len(segments[i].text.split())
                estimated_duration = max(word_count / 2.5, 5.0)  # 150 words per minute
                segments[i].duration = estimated_duration
                segments[i + 1].start = segments[i].start + estimated_duration
            
            # Last segment duration
            last_segment = segments[-1]
            word_count = len(last_segment.text.split())
            last_segment.duration = max(word_count / 2.5, 5.0)
        
        return segments
    
    def merge_segments_by_speaker(self, segments: List[Segment]) -> List[Segment]:
        """
        Merge consecutive segments from the same speaker.
        This helps create more coherent chunks.
        """
        if not segments:
            return []
        
        merged = []
        current_segment = segments[0]
        
        for next_segment in segments[1:]:
            if (next_segment.speaker == current_segment.speaker and
                next_segment.start - (current_segment.start + current_segment.duration) < 5.0):
                # Merge: same speaker and less than 5 seconds gap
                current_segment.text += ' ' + next_segment.text
                current_segment.duration = (next_segment.start + next_segment.duration) - current_segment.start
            else:
                merged.append(current_segment)
                current_segment = next_segment
        
        merged.append(current_segment)
        return merged
    
    def validate_temporal_ordering(self, segments: List[Segment]) -> List[Tuple[int, int]]:
        """
        Validate that segments are in temporal order.
        Returns list of (index1, index2) pairs where ordering is violated.
        """
        violations = []
        
        for i in range(len(segments) - 1):
            current_end = segments[i].start + segments[i].duration
            next_start = segments[i + 1].start
            
            if next_start < current_end:
                violations.append((i, i + 1))
        
        return violations
