"""
Parent Chunk Loader
Loads parent chunks from JSON files for retrieval expansion
"""

import json
from pathlib import Path
from typing import Dict, Optional


class ParentChunkLoader:
    """
    Loads parent chunks from JSON files.
    Builds lookup: (video_id, parent_id) -> parent_chunk_text
    """
    
    def __init__(self, chunks_dir: str = "chunks_product_management"):
        """
        Initialize parent chunk loader.
        
        Args:
            chunks_dir: Directory containing JSON chunk files
        """
        self.chunks_dir = Path(chunks_dir)
        self.parent_lookup: Dict[tuple, Dict[str, any]] = {}
        self._load_all_parents()
    
    def _load_all_parents(self):
        """Load all parent chunks from JSON files."""
        if not self.chunks_dir.exists():
            print(f"Warning: Chunks directory not found: {self.chunks_dir}")
            return
        
        json_files = list(self.chunks_dir.glob("*.json"))
        json_files = [f for f in json_files if f.name != "all_chunks.json"]
        
        print(f"Loading parent chunks from {len(json_files)} episode files...")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    episode_data = json.load(f)
                
                video_id = episode_data.get('metadata', {}).get('video_id', '')
                if not video_id:
                    continue
                
                # Load parent chunks for this episode
                for parent_chunk in episode_data.get('parent_chunks', []):
                    parent_id = parent_chunk.get('id')
                    if parent_id:
                        key = (video_id, parent_id)
                        self.parent_lookup[key] = {
                            'text': parent_chunk.get('text', ''),
                            'start_seconds': parent_chunk.get('start_seconds', 0.0),
                            'end_seconds': parent_chunk.get('end_seconds', 0.0),
                            'video_id': video_id,
                            'parent_id': parent_id,
                            'title': episode_data.get('metadata', {}).get('title', ''),
                            'guest': episode_data.get('metadata', {}).get('guest', ''),
                        }
            
            except Exception as e:
                print(f"Warning: Could not load {json_file}: {e}")
                continue
        
        print(f"Loaded {len(self.parent_lookup)} parent chunks")
    
    def get_parent(self, video_id: str, parent_id: str) -> Optional[Dict[str, any]]:
        """
        Get parent chunk by video_id and parent_id.
        
        Args:
            video_id: Video ID
            parent_id: Parent chunk ID
            
        Returns:
            Parent chunk dictionary or None if not found
        """
        key = (video_id, parent_id)
        return self.parent_lookup.get(key)
    
    def get_stats(self) -> Dict[str, any]:
        """Get loader statistics."""
        return {
            'total_parents': len(self.parent_lookup),
            'chunks_dir': str(self.chunks_dir)
        }
