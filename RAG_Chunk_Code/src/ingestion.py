"""
File-Based Ingestion Module
Reads transcripts from local files and GitHub repositories.
"""

import json
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from pydantic import BaseModel, Field


class Segment(BaseModel):
    """Represents a single transcript segment with temporal and speaker metadata."""
    text: str
    start: float  # Start time in seconds
    duration: float  # Duration in seconds
    speaker: Optional[str] = None


class VideoMetadata(BaseModel):
    """Video metadata extracted from files or provided manually."""
    video_id: str
    title: str
    description: str = ""
    publish_date: str  # ISO8601 format
    view_count: Optional[int] = None
    duration: Optional[float] = None  # Duration in seconds
    guest: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    transcript_source: str = "file"


class IngestedVideo(BaseModel):
    """Complete ingested video data structure."""
    video_id: str
    transcript_source: str
    raw_text: str
    segments: List[Segment]
    meta: VideoMetadata


class FileIngester:
    """Handles reading transcripts from local files."""
    
    def __init__(self, transcripts_dir: str = "transcripts"):
        """
        Initialize file ingester.
        
        Args:
            transcripts_dir: Directory containing transcript files
        """
        self.transcripts_dir = Path(transcripts_dir)
    
    def read_transcript_file(self, file_path: str) -> str:
        """
        Read transcript from a text file.
        
        Args:
            file_path: Path to transcript file
            
        Returns:
            Raw transcript text
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def parse_yaml_frontmatter(self, content: str) -> tuple[Optional[Dict[str, Any]], str]:
        """
        Parse YAML frontmatter from markdown file.
        
        Args:
            content: File content with optional YAML frontmatter
            
        Returns:
            Tuple of (frontmatter_dict, content_without_frontmatter)
        """
        # Check if file starts with frontmatter markers
        if not content.startswith('---'):
            return None, content
        
        # Split by frontmatter markers
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None, content
        
        try:
            frontmatter = yaml.safe_load(parts[1])
            transcript_content = parts[2].strip()
            return frontmatter, transcript_content
        except yaml.YAMLError as e:
            print(f"Warning: Failed to parse YAML frontmatter: {e}")
            return None, content
    
    def extract_metadata_from_filename(self, filename: str) -> Dict[str, Any]:
        """
        Extract metadata from filename patterns.
        Example: "l-T8sNRcWQk_ada-chen-rekhi_2023-04-21.txt"
        """
        metadata = {
            'video_id': '',
            'title': filename,
            'publish_date': datetime.now().strftime('%Y-%m-%d'),
            'guest': None,
            'topics': []
        }
        
        # Try to extract video_id from filename
        parts = Path(filename).stem.split('_')
        if parts:
            # First part might be video_id
            if len(parts[0]) == 11:  # YouTube video IDs are 11 chars
                metadata['video_id'] = parts[0]
            
            # Second part might be guest name
            if len(parts) > 1:
                guest_name = parts[1].replace('-', ' ').title()
                metadata['guest'] = guest_name
        
        return metadata
    
    def extract_guest_name(self, text: str) -> Optional[str]:
        """
        Extract guest name from transcript text.
        Looks for patterns like "Ada Chen Rekhi (00:00:00):"
        """
        # Pattern: "Name (timestamp):"
        pattern = r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+\(\d{1,2}:\d{2}:\d{2}\):'
        matches = re.findall(pattern, text, re.MULTILINE)
        
        if matches:
            # Return the first unique name that's not "Lenny" (assuming host)
            for name in matches:
                if name.lower() != 'lenny':
                    return name
        
        return None
    
    def extract_topics(self, text: str) -> List[str]:
        """
        Extract topic keywords from transcript text.
        """
        topic_keywords = [
            'hiring', 'culture', 'growth', 'roadmap', 'user research',
            'product', 'engineering', 'design', 'marketing', 'sales',
            'startup', 'leadership', 'career', 'pricing', 'strategy',
            'curiosity', 'loop', 'values', 'transition', 'job'
        ]
        
        text_lower = text.lower()
        found_topics = [topic for topic in topic_keywords if topic in text_lower]
        
        return list(set(found_topics))  # Remove duplicates
    
    def parse_chapters(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse chapter timestamps from text.
        Format: (HH:MM:SS) Chapter Title
        """
        chapters = []
        pattern = r'\((\d{1,2}):(\d{2}):(\d{2})\)\s*(.+)'
        
        for line in text.split('\n'):
            match = re.search(pattern, line)
            if match:
                hours, minutes, seconds = map(int, match.groups()[:3])
                title = match.group(4).strip()
                total_seconds = hours * 3600 + minutes * 60 + seconds
                
                chapters.append({
                    'start_seconds': total_seconds,
                    'title': title
                })
        
        return chapters
    
    def ingest_from_file(self, file_path: str, video_id: Optional[str] = None, 
                        metadata_override: Optional[Dict[str, Any]] = None) -> IngestedVideo:
        """
        Ingest transcript from a local file.
        
        Args:
            file_path: Path to transcript file
            video_id: Optional video ID (extracted from filename if not provided)
            metadata_override: Optional metadata to override extracted values
            
        Returns:
            IngestedVideo object
        """
        # Read transcript
        file_content = self.read_transcript_file(file_path)
        
        # Parse YAML frontmatter if present
        frontmatter, raw_text = self.parse_yaml_frontmatter(file_content)
        
        # Initialize metadata
        metadata = {
            'video_id': '',
            'title': Path(file_path).stem,
            'description': '',
            'publish_date': datetime.now().strftime('%Y-%m-%d'),
            'view_count': None,
            'duration': None,
            'guest': None,
            'topics': []
        }
        
        # Extract metadata from YAML frontmatter if available
        if frontmatter:
            metadata['guest'] = frontmatter.get('guest')
            metadata['title'] = frontmatter.get('title', metadata['title'])
            metadata['description'] = frontmatter.get('description', '')
            
            # Handle publish_date - convert date object to string if needed
            publish_date = frontmatter.get('publish_date', metadata['publish_date'])
            if publish_date:
                if isinstance(publish_date, date):
                    metadata['publish_date'] = publish_date.strftime('%Y-%m-%d')
                elif isinstance(publish_date, datetime):
                    metadata['publish_date'] = publish_date.strftime('%Y-%m-%d')
                else:
                    metadata['publish_date'] = str(publish_date)
            else:
                metadata['publish_date'] = metadata['publish_date']
            
            metadata['view_count'] = frontmatter.get('view_count')
            metadata['duration'] = frontmatter.get('duration_seconds')
            
            # Extract video_id from frontmatter or YouTube URL
            if frontmatter.get('video_id'):
                metadata['video_id'] = frontmatter['video_id']
            elif frontmatter.get('youtube_url'):
                # Extract video ID from YouTube URL
                youtube_url = frontmatter['youtube_url']
                video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', youtube_url)
                if video_id_match:
                    metadata['video_id'] = video_id_match.group(1)
        
        # Fallback: Extract metadata from filename if frontmatter not available
        if not frontmatter:
            filename = Path(file_path).name
            file_metadata = self.extract_metadata_from_filename(filename)
            metadata.update({k: v for k, v in file_metadata.items() if not metadata.get(k)})
        
        # Extract guest and topics from text if not in frontmatter
        if not metadata.get('guest'):
            guest = self.extract_guest_name(raw_text)
            if guest:
                metadata['guest'] = guest
        
        topics = self.extract_topics(raw_text)
        if topics:
            metadata['topics'].extend(topics)
        
        # Override with provided metadata
        if metadata_override:
            metadata.update(metadata_override)
        
        # Use provided video_id or generate placeholder
        if video_id:
            metadata['video_id'] = video_id
        elif not metadata['video_id']:
            # Generate a placeholder ID from filename
            metadata['video_id'] = Path(file_path).stem.replace('_', '-')[:11]
        
        # Create metadata object
        meta = VideoMetadata(**metadata)
        
        # FIX 1: Segments are created ONLY by TranscriptParser, not here
        # Return empty segments list - parser will create them
        segments = []
        
        # Create ingested video object
        ingested = IngestedVideo(
            video_id=metadata['video_id'],
            transcript_source="file",
            raw_text=raw_text,
            segments=segments,
            meta=meta
        )
        
        return ingested
    
    def ingest_from_directory(self, directory: Optional[str] = None) -> List[IngestedVideo]:
        """
        Ingest all transcript files from a directory.
        
        Args:
            directory: Directory path (uses self.transcripts_dir if not provided)
            
        Returns:
            List of IngestedVideo objects
        """
        dir_path = Path(directory) if directory else self.transcripts_dir
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
        
        # Find all text files
        transcript_files = list(dir_path.glob("*.txt")) + list(dir_path.glob("*.md"))
        
        ingested_videos = []
        for file_path in transcript_files:
            try:
                ingested = self.ingest_from_file(str(file_path))
                ingested_videos.append(ingested)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        return ingested_videos
