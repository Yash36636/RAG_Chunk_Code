"""
Embedding Pipeline Script
Processes JSON chunks and creates two-tier embeddings (core + longtail).
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src import (
    EmbeddingGenerator,
    PineconeStore,
    TwoTierEmbeddingPipeline,
    ChunkClassifier,
    ParentChildChunk,
    VideoMetadata
)
from src.storage import ChunkStorage


def load_chunks_from_json(json_file: Path) -> Dict[str, Any]:
    """
    Load chunks from JSON file.
    
    Args:
        json_file: Path to JSON file
        
    Returns:
        Dictionary with episode data
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def chunks_from_json_data(episode_data: Dict[str, Any]) -> tuple:
    """
    Convert JSON data to ParentChildChunk objects.
    
    Args:
        episode_data: Episode data from JSON
        
    Returns:
        Tuple of (parent_chunks, child_chunks, metadata, enriched_texts)
    """
    # Create metadata
    meta_dict = episode_data['metadata']
    metadata = VideoMetadata(
        video_id=meta_dict.get('video_id', ''),
        title=meta_dict.get('title', ''),
        guest=meta_dict.get('guest', ''),
        publish_date=meta_dict.get('publish_date', ''),
        topics=meta_dict.get('topics', []),
        description=meta_dict.get('description', ''),
        view_count=meta_dict.get('view_count'),
        duration=meta_dict.get('duration')
    )
    
    # Create parent chunks
    parent_chunks = []
    for p_dict in episode_data.get('parent_chunks', []):
        chunk = ParentChildChunk(
            text=p_dict['text'],
            start_seconds=p_dict['start_seconds'],
            end_seconds=p_dict['end_seconds'],
            chunk_type='parent'
        )
        chunk.id = p_dict['id']
        parent_chunks.append(chunk)
    
    # Create child chunks
    child_chunks = []
    enriched_texts = []
    for c_dict in episode_data.get('child_chunks', []):
        chunk = ParentChildChunk(
            text=c_dict['text'],
            start_seconds=c_dict['start_seconds'],
            end_seconds=c_dict['end_seconds'],
            speaker=c_dict.get('speaker'),
            parent_id=c_dict.get('parent_id'),
            chunk_type='child'
        )
        chunk.id = c_dict['id']
        child_chunks.append(chunk)
        enriched_texts.append(c_dict.get('enriched_text', c_dict['text']))
    
    return parent_chunks, child_chunks, metadata, enriched_texts


def embed_all_chunks(
    chunks_dir: str,
    openai_api_key: str,
    pinecone_api_key: str,
    pinecone_environment: str,
    core_index_name: str = "product-management-core",
    longtail_index_name: str = "product-management-longtail",
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Embed all chunks from JSON files.
    
    Args:
        chunks_dir: Directory containing JSON chunk files
        openai_api_key: OpenAI API key
        pinecone_api_key: Pinecone API key
        pinecone_environment: Pinecone environment
        core_index_name: Name of core index
        longtail_index_name: Name of longtail index
        batch_size: Batch size for processing
        
    Returns:
        Dictionary with embedding statistics
    """
    chunks_path = Path(chunks_dir)
    if not chunks_path.exists():
        raise ValueError(f"Chunks directory not found: {chunks_dir}")
    
    # Find all JSON files
    json_files = list(chunks_path.glob("*.json"))
    # Exclude consolidated file
    json_files = [f for f in json_files if f.name != "all_chunks.json"]
    
    print(f"Found {len(json_files)} episode JSON files")
    
    # Initialize embedding components
    embedding_generator = EmbeddingGenerator(
        model_name="text-embedding-3-large",
        dimensions=1536,
        api_key=openai_api_key
    )
    
    core_store = PineconeStore(
        api_key=pinecone_api_key,
        environment=pinecone_environment,
        index_name=core_index_name
    )
    
    longtail_store = PineconeStore(
        api_key=pinecone_api_key,
        environment=pinecone_environment,
        index_name=longtail_index_name
    )
    
    two_tier_pipeline = TwoTierEmbeddingPipeline(
        embedding_generator=embedding_generator,
        core_store=core_store,
        longtail_store=longtail_store
    )
    
    # Process episodes
    total_stats = {
        "total_episodes": 0,
        "total_chunks": 0,
        "core_chunks": 0,
        "longtail_chunks": 0,
        "skipped_chunks": 0,
        "episodes_processed": []
    }
    
    print("\n" + "="*70)
    print("Starting Embedding Process")
    print("="*70)
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] Processing: {json_file.name}")
        
        try:
            # Load episode data
            episode_data = load_chunks_from_json(json_file)
            
            # Convert to chunk objects
            parent_chunks, child_chunks, metadata, enriched_texts = chunks_from_json_data(episode_data)
            
            print(f"  Episodes: {metadata.title or 'N/A'}")
            print(f"  Guest: {metadata.guest or 'N/A'}")
            print(f"  Child chunks: {len(child_chunks)}")
            
            # Index chunks
            stats = two_tier_pipeline.index_chunks(
                child_chunks=child_chunks,
                parent_chunks=parent_chunks,
                metadata=metadata,
                enriched_texts=enriched_texts
            )
            
            print(f"  Core chunks indexed: {stats['core_chunks']}")
            print(f"  Longtail chunks indexed: {stats['longtail_chunks']}")
            print(f"  Skipped chunks: {stats['skipped_chunks']}")
            
            # Update totals
            total_stats["total_episodes"] += 1
            total_stats["total_chunks"] += stats["total_chunks"]
            total_stats["core_chunks"] += stats["core_chunks"]
            total_stats["longtail_chunks"] += stats["longtail_chunks"]
            total_stats["skipped_chunks"] += stats["skipped_chunks"]
            total_stats["episodes_processed"].append({
                "episode_id": metadata.video_id,
                "title": metadata.title,
                "stats": stats
            })
            
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "="*70)
    print("Embedding Complete")
    print("="*70)
    print(f"Total episodes processed: {total_stats['total_episodes']}")
    print(f"Total chunks: {total_stats['total_chunks']}")
    print(f"Core chunks: {total_stats['core_chunks']}")
    print(f"Longtail chunks: {total_stats['longtail_chunks']}")
    print(f"Skipped chunks: {total_stats['skipped_chunks']}")
    print(f"\nCore index: {core_index_name}")
    print(f"Longtail index: {longtail_index_name}")
    print("="*70)
    
    return total_stats


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Embed chunks from JSON files into two-tier vector indexes"
    )
    parser.add_argument(
        "--chunks-dir",
        type=str,
        default="chunks_product_management",
        help="Directory containing JSON chunk files (default: chunks_product_management)"
    )
    parser.add_argument(
        "--openai-key",
        type=str,
        help="OpenAI API key (or set OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--pinecone-key",
        type=str,
        help="Pinecone API key (or set PINECONE_API_KEY env var)"
    )
    parser.add_argument(
        "--pinecone-env",
        type=str,
        help="Pinecone environment (or set PINECONE_ENVIRONMENT env var)"
    )
    parser.add_argument(
        "--core-index",
        type=str,
        default="product-management-core",
        help="Core index name (default: product-management-core)"
    )
    parser.add_argument(
        "--longtail-index",
        type=str,
        default="product-management-longtail",
        help="Longtail index name (default: product-management-longtail)"
    )
    
    args = parser.parse_args()
    
    # Get API keys
    openai_key = args.openai_key or os.getenv("OPENAI_API_KEY")
    pinecone_key = args.pinecone_key or os.getenv("PINECONE_API_KEY")
    pinecone_env = args.pinecone_env or os.getenv("PINECONE_ENVIRONMENT")
    
    if not openai_key:
        raise ValueError("OpenAI API key required (--openai-key or OPENAI_API_KEY env var)")
    if not pinecone_key:
        raise ValueError("Pinecone API key required (--pinecone-key or PINECONE_API_KEY env var)")
    if not pinecone_env:
        raise ValueError("Pinecone environment required (--pinecone-env or PINECONE_ENVIRONMENT env var)")
    
    # Run embedding
    stats = embed_all_chunks(
        chunks_dir=args.chunks_dir,
        openai_api_key=openai_key,
        pinecone_api_key=pinecone_key,
        pinecone_environment=pinecone_env,
        core_index_name=args.core_index,
        longtail_index_name=args.longtail_index
    )
    
    print("\nEmbedding complete!")
    return stats


if __name__ == "__main__":
    main()
