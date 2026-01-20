"""
Free Retrieval Script
Query the FAISS indexes using free Sentence Transformers models
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

# Set environment variables to prevent TensorFlow import errors
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src import (
    TwoTierEmbeddingPipeline,
    RetrievalPipeline,
    RetrievalResult
)
from src.free_embedding import FreeEmbeddingGenerator
from src.faiss_store import FAISSStore
from src.parent_loader import ParentChunkLoader


def initialize_retrieval_pipeline(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    device: Optional[str] = None,
    core_index_path: str = "./faiss_indexes/product-management-core",
    longtail_index_path: str = "./faiss_indexes/product-management-longtail",
    min_score_threshold: float = 0.3
) -> RetrievalPipeline:
    """
    Initialize retrieval pipeline with free models.
    
    Args:
        model_name: Sentence Transformers model name
        device: Device to use (auto-detects if None)
        core_index_path: Path to core FAISS index
        longtail_index_path: Path to longtail FAISS index
        
    Returns:
        Initialized RetrievalPipeline
    """
    # Determine dimension
    dimension_map = {
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-mpnet-base-v2": 768,
        "intfloat/e5-large-v2": 1024,
        "intfloat/e5-small-v2": 384,
        "intfloat/e5-base-v2": 768,
    }
    dimension = dimension_map.get(model_name, 384)
    
    # Initialize embedding generator
    embedding_generator = FreeEmbeddingGenerator(
        model_name=model_name,
        device=device
    )
    
    # Initialize vector stores
    core_store = FAISSStore(
        index_path=core_index_path,
        dimension=dimension
    )
    
    longtail_store = FAISSStore(
        index_path=longtail_index_path,
        dimension=dimension
    )
    
    # Initialize two-tier pipeline (for parent lookup)
    two_tier_pipeline = TwoTierEmbeddingPipeline(
        embedding_generator=embedding_generator,
        core_store=core_store,
        longtail_store=longtail_store
    )
    
    # Initialize retrieval pipeline
    retrieval_pipeline = RetrievalPipeline(
        embedding_generator=embedding_generator,
        core_store=core_store,
        longtail_store=longtail_store,
        two_tier_pipeline=two_tier_pipeline,
        core_top_k=20,  # STEP 2.2: Increased for better recall
        longtail_top_k=10,
        min_score_threshold=min_score_threshold,  # FIX: Configurable threshold (default 0.3)
        parent_expansion_percent=0.25
    )
    
    return retrieval_pipeline


def format_retrieval_results(results: List[RetrievalResult], retrieval_pipeline: RetrievalPipeline) -> str:
    """
    Format retrieval results for display.
    
    Args:
        results: List of retrieval results
        retrieval_pipeline: Retrieval pipeline (for deep link generation)
        
    Returns:
        Formatted string
    """
    if not results:
        return "No results found."
    
    lines = []
    lines.append(f"\nFound {len(results)} results:\n")
    lines.append("="*70)
    
    for i, result in enumerate(results, 1):
        lines.append(f"\n[{i}] Score: {result.score:.3f} | Tier: {result.tier}")
        lines.append(f"    Video: {result.video_id}")
        lines.append(f"    Time: {int(result.start_seconds//60)}m{int(result.start_seconds%60)}s")
        if result.speaker:
            lines.append(f"    Speaker: {result.speaker}")
        
        # Deep link
        deep_link = retrieval_pipeline.create_deep_link(
            result.video_id,
            result.start_seconds
        )
        lines.append(f"    Link: {deep_link}")
        
        lines.append(f"\n    Text: {result.text[:200]}...")
        
        if result.parent_text:
            lines.append(f"\n    Parent Context: {result.parent_text[:200]}...")
        
        lines.append("-"*70)
    
    return "\n".join(lines)


def query(
    query_text: str,
    retrieval_pipeline: RetrievalPipeline,
    use_longtail: bool = False,
    filters: Optional[dict] = None
) -> List[RetrievalResult]:
    """
    Query the vector indexes.
    
    Args:
        query_text: Search query
        retrieval_pipeline: Initialized retrieval pipeline
        use_longtail: Whether to search longtail index
        filters: Optional metadata filters
        
    Returns:
        List of retrieval results
    """
    results = retrieval_pipeline.retrieve(
        query=query_text,
        use_longtail=use_longtail,
        filters=filters
    )
    
    return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Query the FAISS indexes using free Sentence Transformers models"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Search query"
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
        help="Path to core FAISS index"
    )
    parser.add_argument(
        "--longtail-index",
        type=str,
        default="./faiss_indexes/product-management-longtail",
        help="Path to longtail FAISS index"
    )
    parser.add_argument(
        "--use-longtail",
        action="store_true",
        help="Also search longtail index"
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.3,
        help="Minimum similarity score threshold (default: 0.3)"
    )
    parser.add_argument(
        "--chunks-dir",
        type=str,
        default="chunks_product_management",
        help="Directory containing JSON chunk files (for parent expansion)"
    )
    parser.add_argument(
        "--no-parent-expansion",
        action="store_true",
        help="Don't use full parent expansion (use fallback)"
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    print(f"Initializing retrieval pipeline with model: {args.model}...")
    retrieval_pipeline = initialize_retrieval_pipeline(
        model_name=args.model,
        device=args.device,
        core_index_path=args.core_index,
        longtail_index_path=args.longtail_index,
        min_score_threshold=args.min_score
    )
    
    # STEP 2: Load parent chunks for full expansion
    parent_loader = None
    if not args.no_parent_expansion:
        print("Loading parent chunks for full expansion...")
        try:
            parent_loader = ParentChunkLoader(chunks_dir=args.chunks_dir)
            print(f"Loaded {parent_loader.get_stats()['total_parents']} parent chunks")
        except Exception as e:
            print(f"Warning: Could not load parent chunks: {e}")
            print("Falling back to standard retrieval")
    
    # Query
    print(f"\nQuerying: {args.query}")
    if parent_loader:
        # Use parent loader for full expansion (STEP 1 + 2)
        results = retrieval_pipeline.retrieve_with_parent_loader(
            query=args.query,
            parent_loader=parent_loader,
            use_longtail=args.use_longtail,
            use_query_rewriting=True
        )
    else:
        # Fallback: standard retrieval
        results = query(
            query_text=args.query,
            retrieval_pipeline=retrieval_pipeline,
            use_longtail=args.use_longtail
        )
    
    # Display results
    print(format_retrieval_results(results, retrieval_pipeline))
    
    return results


if __name__ == "__main__":
    main()
