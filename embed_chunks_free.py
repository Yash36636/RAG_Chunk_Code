"""
Free Embedding Pipeline Script
Uses Sentence Transformers + FAISS (no API keys needed, runs locally)
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

# Set environment variables to prevent TensorFlow import errors
# (sentence-transformers uses PyTorch, not TensorFlow)
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src import (
    TwoTierEmbeddingPipeline,
    ParentChildChunk,
    VideoMetadata
)
from src.free_embedding import FreeEmbeddingGenerator
from src.faiss_store import FAISSStore
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
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    device: Optional[str] = None,
    core_index_path: str = "./faiss_indexes/product-management-core",
    longtail_index_path: str = "./faiss_indexes/product-management-longtail",
    batch_size: int = 64
) -> Dict[str, Any]:
    """
    Embed all chunks from JSON files using free models.
    
    Args:
        chunks_dir: Directory containing JSON chunk files
        model_name: Sentence Transformers model name
            - "sentence-transformers/all-MiniLM-L6-v2" (384 dims, fast) - RECOMMENDED
            - "sentence-transformers/all-mpnet-base-v2" (768 dims, better quality)
            - "intfloat/e5-large-v2" (1024 dims, best quality, needs GPU)
            - "intfloat/e5-small-v2" (384 dims, good quality)
        device: "cuda" for GPU, "cpu" for CPU (auto-detects if None)
        core_index_path: Path for core FAISS index
        longtail_index_path: Path for longtail FAISS index
        batch_size: Batch size for embedding generation
        
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
    
    # Determine embedding dimension based on model
    dimension_map = {
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-mpnet-base-v2": 768,
        "intfloat/e5-large-v2": 1024,
        "intfloat/e5-small-v2": 384,
        "intfloat/e5-base-v2": 768,
    }
    
    dimension = dimension_map.get(model_name, 384)
    print(f"Using model: {model_name} ({dimension} dimensions)")
    
    # Initialize embedding components
    embedding_generator = FreeEmbeddingGenerator(
        model_name=model_name,
        device=device
    )
    
    core_store = FAISSStore(
        index_path=core_index_path,
        dimension=dimension
    )
    
    longtail_store = FAISSStore(
        index_path=longtail_index_path,
        dimension=dimension
    )
    
    two_tier_pipeline = TwoTierEmbeddingPipeline(
        embedding_generator=embedding_generator,
        core_store=core_store,
        longtail_store=longtail_store
    )
    
    # Note: batch_size is handled by FreeEmbeddingGenerator.embed_batch()
    # The two_tier_pipeline will call embed_batch with show_progress=True
    # We can't easily override it here, but the default batch_size=64 is good
    
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
    print("Starting Free Embedding Process")
    print("="*70)
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] Processing: {json_file.name}")
        
        try:
            # Load episode data
            episode_data = load_chunks_from_json(json_file)
            
            # Convert to chunk objects
            parent_chunks, child_chunks, metadata, enriched_texts = chunks_from_json_data(episode_data)
            
            print(f"  Episode: {metadata.title or 'N/A'}")
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
    
    # Final statistics
    print("\n" + "="*70)
    print("Embedding Complete")
    print("="*70)
    print(f"Total episodes processed: {total_stats['total_episodes']}")
    print(f"Total chunks: {total_stats['total_chunks']}")
    print(f"Core chunks: {total_stats['core_chunks']}")
    print(f"Longtail chunks: {total_stats['longtail_chunks']}")
    print(f"Skipped chunks: {total_stats['skipped_chunks']}")
    print(f"\nCore index: {core_index_path}")
    print(f"Longtail index: {longtail_index_path}")
    print(f"\nIndex statistics:")
    print(f"  Core: {core_store.get_stats()}")
    print(f"  Longtail: {longtail_store.get_stats()}")
    print("="*70)
    
    return total_stats


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Embed chunks from JSON files using free Sentence Transformers models"
    )
    parser.add_argument(
        "--chunks-dir",
        type=str,
        default="chunks_product_management",
        help="Directory containing JSON chunk files (default: chunks_product_management)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        choices=[
            "sentence-transformers/all-MiniLM-L6-v2",
            "sentence-transformers/all-mpnet-base-v2",
            "intfloat/e5-large-v2",
            "intfloat/e5-small-v2",
            "intfloat/e5-base-v2"
        ],
        help="Sentence Transformers model name (default: all-MiniLM-L6-v2)"
    )
    parser.add_argument(
        "--device",
        type=str,
        choices=["cpu", "cuda"],
        help="Device to use (auto-detects if not specified)"
    )
    parser.add_argument(
        "--core-index",
        type=str,
        default="./faiss_indexes/product-management-core",
        help="Path for core FAISS index (default: ./faiss_indexes/product-management-core)"
    )
    parser.add_argument(
        "--longtail-index",
        type=str,
        default="./faiss_indexes/product-management-longtail",
        help="Path for longtail FAISS index (default: ./faiss_indexes/product-management-longtail)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size for embedding generation (default: 64)"
    )
    
    args = parser.parse_args()
    
    # Run embedding
    stats = embed_all_chunks(
        chunks_dir=args.chunks_dir,
        model_name=args.model,
        device=args.device,
        core_index_path=args.core_index,
        longtail_index_path=args.longtail_index,
        batch_size=args.batch_size
    )
    
    print("\nEmbedding complete!")
    print("\nNext steps:")
    print("1. Test retrieval with: python retrieve_chunks_free.py --query 'your query'")
    print("2. Compare models with: python test_models.py")
    
    return stats


if __name__ == "__main__":
    main()
