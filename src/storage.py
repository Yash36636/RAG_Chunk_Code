"""
JSON Storage Module
Handles saving and loading chunks to/from JSON format.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from .chunking import ParentChildChunk
from .ingestion import VideoMetadata, Segment


class ChunkStorage:
    """Handles storage of processed chunks in JSON format."""
    
    def __init__(self, output_dir: str = "chunks_output"):
        """
        Initialize chunk storage.
        
        Args:
            output_dir: Directory to save JSON files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def chunk_to_dict(self, chunk: ParentChildChunk, metadata: VideoMetadata, 
                      enriched_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert a chunk to a dictionary for JSON serialization.
        
        FIX 5: Use chunk.id directly - no rewriting. Fail if ID is None.
        
        Args:
            chunk: ParentChildChunk instance
            metadata: Video metadata
            enriched_text: Optional enriched text for embedding (must be provided for child chunks)
            
        Returns:
            Dictionary representation of the chunk
        """
        # FIX 5: Use chunk.id directly - raise error if None (no silent fallback)
        if chunk.id is None:
            raise ValueError(
                f"Chunk {chunk.chunk_type} has no ID assigned. "
                f"IDs must be assigned during chunking, not in storage."
            )
        
        chunk_dict = {
            'id': chunk.id,
            'text': chunk.text,
            'enriched_text': enriched_text if enriched_text is not None else chunk.text,
            'start_seconds': chunk.start_seconds,
            'end_seconds': chunk.end_seconds,
            'duration_seconds': chunk.end_seconds - chunk.start_seconds,
            'speaker': chunk.speaker,
            'chunk_type': chunk.chunk_type,
            'parent_id': chunk.parent_id,
            'video_metadata': {
                'video_id': metadata.video_id,
                'title': metadata.title,
                'guest': metadata.guest,
                'publish_date': metadata.publish_date,
                'topics': metadata.topics,
                'description': metadata.description,
            }
        }
        
        # Add YouTube deep link if video_id is available
        if metadata.video_id:
            start_min = int(chunk.start_seconds // 60)
            start_sec = int(chunk.start_seconds % 60)
            chunk_dict['youtube_url'] = (
                f"https://www.youtube.com/watch?v={metadata.video_id}"
                f"&t={start_min}m{start_sec}s"
            )
        
        return chunk_dict
    
    def save_episode_chunks(self, episode_id: str, parent_chunks: List[ParentChildChunk],
                           child_chunks: List[ParentChildChunk], metadata: VideoMetadata,
                           enriched_texts: Optional[List[str]] = None) -> Path:
        """
        Save chunks for a single episode to JSON.
        
        FIX 4: Storage must never recompute enrichment - use provided enriched_texts only.
        
        Args:
            episode_id: Unique identifier for the episode
            parent_chunks: List of parent chunks
            child_chunks: List of child chunks
            metadata: Video metadata
            enriched_texts: REQUIRED list of enriched texts (one per child chunk)
            
        Returns:
            Path to saved JSON file
        """
        # FIX 4: Require enriched_texts - no recomputation in storage
        if enriched_texts is None:
            raise ValueError(
                "enriched_texts is required. Enrichment must happen in pipeline, not storage."
            )
        if len(enriched_texts) != len(child_chunks):
            raise ValueError(
                f"enriched_texts length ({len(enriched_texts)}) doesn't match "
                f"child_chunks length ({len(child_chunks)}). "
                f"Enrichment must happen in pipeline with correct alignment."
            )
        
        # Prepare enriched texts mapping by index (not by ID)
        # FIX 5: Use index-based mapping since IDs are guaranteed sequential
        enriched_map = {i: enriched_texts[i] for i in range(len(enriched_texts))}
        
        # Convert chunks to dictionaries
        parent_chunks_dict = [
            self.chunk_to_dict(chunk, metadata) 
            for chunk in parent_chunks
        ]
        
        child_chunks_dict = [
            self.chunk_to_dict(
                chunk, 
                metadata, 
                enriched_text=enriched_map[i]
            )
            for i, chunk in enumerate(child_chunks)
        ]
        
        # Create episode data structure
        episode_data = {
            'episode_id': episode_id,
            'metadata': {
                'video_id': metadata.video_id,
                'title': metadata.title,
                'guest': metadata.guest,
                'publish_date': metadata.publish_date,
                'topics': metadata.topics,
                'description': metadata.description,
                'view_count': metadata.view_count,
                'duration': metadata.duration,
            },
            'statistics': {
                'total_parent_chunks': len(parent_chunks),
                'total_child_chunks': len(child_chunks),
                'total_segments': len(parent_chunks) + len(child_chunks),
            },
            'parent_chunks': parent_chunks_dict,
            'child_chunks': child_chunks_dict,
            'processed_at': datetime.now().isoformat(),
        }
        
        # Save to JSON file
        output_file = self.output_dir / f"{episode_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(episode_data, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def save_all_chunks(self, all_episodes: List[Dict[str, Any]], 
                       output_file: str = "all_chunks.json") -> Path:
        """
        Save all chunks from multiple episodes to a single JSON file.
        
        Args:
            all_episodes: List of episode processing results
            output_file: Name of output JSON file
            
        Returns:
            Path to saved JSON file
        """
        all_data = {
            'total_episodes': len(all_episodes),
            'processed_at': datetime.now().isoformat(),
            'episodes': []
        }
        
        total_parent_chunks = 0
        total_child_chunks = 0
        
        for episode_result in all_episodes:
            metadata = episode_result['metadata']
            parent_chunks = episode_result['parent_chunks']
            child_chunks = episode_result['child_chunks']
            enriched_texts = episode_result.get('enriched_texts', [])
            
            # FIX 4: Require enriched_texts - no recomputation in storage
            if not enriched_texts:
                raise ValueError(
                    "enriched_texts is required. Enrichment must happen in pipeline, not storage."
                )
            if len(enriched_texts) != len(child_chunks):
                raise ValueError(
                    f"enriched_texts length ({len(enriched_texts)}) doesn't match "
                    f"child_chunks length ({len(child_chunks)}). "
                    f"Enrichment must happen in pipeline with correct alignment."
                )
            
            # FIX 5: Use index-based mapping since IDs are guaranteed sequential
            enriched_map = {i: enriched_texts[i] for i in range(len(enriched_texts))}
            
            # Convert chunks to dictionaries
            parent_chunks_dict = [
                self.chunk_to_dict(chunk, metadata) 
                for chunk in parent_chunks
            ]
            
            child_chunks_dict = [
                self.chunk_to_dict(
                    chunk, 
                    metadata, 
                    enriched_text=enriched_map[i]
                )
                for i, chunk in enumerate(child_chunks)
            ]
            
            episode_data = {
                'episode_id': metadata.video_id or metadata.title,
                'metadata': {
                    'video_id': metadata.video_id,
                    'title': metadata.title,
                    'guest': metadata.guest,
                    'publish_date': metadata.publish_date,
                    'topics': metadata.topics,
                    'description': metadata.description,
                    'view_count': metadata.view_count,
                    'duration': metadata.duration,
                },
                'statistics': {
                    'total_parent_chunks': len(parent_chunks),
                    'total_child_chunks': len(child_chunks),
                },
                'parent_chunks': parent_chunks_dict,
                'child_chunks': child_chunks_dict,
            }
            
            all_data['episodes'].append(episode_data)
            total_parent_chunks += len(parent_chunks)
            total_child_chunks += len(child_chunks)
        
        all_data['total_statistics'] = {
            'total_parent_chunks': total_parent_chunks,
            'total_child_chunks': total_child_chunks,
            'total_chunks': total_parent_chunks + total_child_chunks,
        }
        
        # Save to JSON file
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def load_episode_chunks(self, episode_id: str) -> Dict[str, Any]:
        """
        Load chunks for a single episode from JSON.
        
        Args:
            episode_id: Episode identifier
            
        Returns:
            Dictionary with episode data
        """
        input_file = self.output_dir / f"{episode_id}.json"
        if not input_file.exists():
            raise FileNotFoundError(f"Chunk file not found: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
