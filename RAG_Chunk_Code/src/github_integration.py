"""
GitHub Integration Module
Handles cloning repositories and reading files from GitHub.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import requests
from urllib.parse import urlparse


class GitHubRepo:
    """Handles GitHub repository operations."""
    
    def __init__(self, repo_url: str, local_path: Optional[str] = None):
        """
        Initialize GitHub repository handler.
        
        Args:
            repo_url: GitHub repository URL (e.g., https://github.com/user/repo)
            local_path: Local path to clone/store the repo (default: ./repo_name)
        """
        self.repo_url = repo_url
        self.repo_name = self._extract_repo_name(repo_url)
        self.local_path = Path(local_path) if local_path else Path(self.repo_name)
    
    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL."""
        parsed = urlparse(url)
        # Extract repo name from path (e.g., /user/repo or /user/repo.git -> repo)
        parts = parsed.path.strip('/').split('/')
        if len(parts) >= 2:
            repo_name = parts[-1]
            # Remove .git suffix if present
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            return repo_name
        return "repo"
    
    def clone(self, force: bool = False) -> Path:
        """
        Clone the repository locally.
        
        Args:
            force: If True, remove existing directory and re-clone
            
        Returns:
            Path to cloned repository
        """
        if self.local_path.exists() and force:
            import shutil
            shutil.rmtree(self.local_path)
        
        if not self.local_path.exists():
            print(f"Cloning repository {self.repo_url}...")
            subprocess.run(
                ["git", "clone", self.repo_url, str(self.local_path)],
                check=True,
                capture_output=True
            )
            print(f"Repository cloned to {self.local_path}")
        else:
            print(f"Repository already exists at {self.local_path}")
        
        return self.local_path
    
    def pull(self):
        """Pull latest changes from repository."""
        if self.local_path.exists():
            print("Pulling latest changes...")
            subprocess.run(
                ["git", "pull"],
                cwd=self.local_path,
                check=True,
                capture_output=True
            )
            print("Repository updated")
    
    def read_file(self, file_path: str) -> str:
        """
        Read a file from the cloned repository.
        
        Args:
            file_path: Relative path from repo root (e.g., "index/product-management.md")
            
        Returns:
            File contents as string
        """
        full_path = self.local_path / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def list_transcript_files(self, episodes_dir: str = "episodes") -> List[str]:
        """
        List all transcript files in the episodes directory.
        
        Args:
            episodes_dir: Directory containing episodes
            
        Returns:
            List of transcript file paths
        """
        episodes_path = self.local_path / episodes_dir
        if not episodes_path.exists():
            return []
        
        transcript_files = []
        for guest_dir in episodes_path.iterdir():
            if guest_dir.is_dir():
                transcript_path = guest_dir / "transcript.md"
                if transcript_path.exists():
                    transcript_files.append(str(transcript_path.relative_to(self.local_path)))
        
        return transcript_files
    
    def get_transcript_path(self, guest_name: str, episodes_dir: str = "episodes") -> Optional[Path]:
        """
        Get the transcript path for a specific guest.
        
        Args:
            guest_name: Name of the guest
            episodes_dir: Directory containing episodes
            
        Returns:
            Path to transcript file or None if not found
        """
        # Try different name formats
        name_variants = [
            guest_name,
            guest_name.lower(),
            guest_name.replace(' ', '-'),
            guest_name.replace(' ', '_'),
        ]
        
        episodes_path = self.local_path / episodes_dir
        for variant in name_variants:
            transcript_path = episodes_path / variant / "transcript.md"
            if transcript_path.exists():
                return transcript_path
        
        return None


class TopicIndexParser:
    """Parses topic index files to extract episode references."""
    
    def __init__(self, repo: GitHubRepo):
        """
        Initialize parser.
        
        Args:
            repo: GitHubRepo instance
        """
        self.repo = repo
    
    def parse_topic_file(self, topic_file: str) -> Dict[str, any]:
        """
        Parse a topic index file (e.g., product-management.md) to extract episode references.
        
        Args:
            topic_file: Path to topic file (e.g., "index/product-management.md")
            
        Returns:
            Dictionary with parsed information
        """
        content = self.repo.read_file(topic_file)
        
        # Extract episode references
        # Common patterns:
        # - [Episode Title](episodes/guest-name/transcript.md)
        # - episodes/guest-name/transcript.md
        # - Guest Name - Episode Title
        
        episodes = []
        
        # Pattern 1: Markdown links
        link_pattern = r'\[([^\]]+)\]\(episodes/([^/]+)/transcript\.md\)'
        for match in re.finditer(link_pattern, content):
            episode_title = match.group(1)
            guest_name = match.group(2)
            episodes.append({
                'title': episode_title,
                'guest': guest_name,
                'path': f"episodes/{guest_name}/transcript.md"
            })
        
        # Pattern 2: Direct file paths
        path_pattern = r'episodes/([^/\s]+)/transcript\.md'
        for match in re.finditer(path_pattern, content):
            guest_name = match.group(1)
            if not any(ep['guest'] == guest_name for ep in episodes):
                episodes.append({
                    'title': None,
                    'guest': guest_name,
                    'path': f"episodes/{guest_name}/transcript.md"
                })
        
        # Pattern 3: Guest names mentioned in headings or lists
        # Look for headings like "## Guest Name" or "- Guest Name"
        heading_pattern = r'^##+\s+(.+)$'
        list_pattern = r'^[-*]\s+(.+)$'
        
        for line in content.split('\n'):
            # Check headings
            heading_match = re.match(heading_pattern, line)
            if heading_match:
                potential_guest = heading_match.group(1).strip()
                if not any(ep['guest'].lower() == potential_guest.lower() for ep in episodes):
                    # Try to find corresponding transcript
                    transcript_path = self.repo.get_transcript_path(potential_guest)
                    if transcript_path:
                        episodes.append({
                            'title': potential_guest,
                            'guest': potential_guest,
                            'path': str(transcript_path.relative_to(self.repo.local_path))
                        })
        
        return {
            'topic_file': topic_file,
            'episodes': episodes,
            'total_episodes': len(episodes)
        }
    
    def get_episode_paths(self, topic_file: str) -> List[str]:
        """
        Get list of transcript file paths from a topic file.
        
        Args:
            topic_file: Path to topic file
            
        Returns:
            List of transcript file paths relative to repo root
        """
        parsed = self.parse_topic_file(topic_file)
        return [ep['path'] for ep in parsed['episodes']]
