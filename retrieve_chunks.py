"""
Retrieval Script
Query the two-tier vector indexes with parent expansion and deduplication.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src import (
    EmbeddingGenerator,
    PineconeStore,
    TwoTierEmbeddingPipeline,
    RetrievalPipeline,
    RetrievalResult
)


def initialize_retrieval_pipeline(
    openai_api_key: str,
    pinecone_api_key: str,
    pinecone_environment: str,
    core_index_name: str = "product-management-core",
    longtail_index_name: str = "product-management-longtail"
) -> RetrievalPipeline:
    """
    Initialize retrieval pipeline.
    
    Args:
        openai_api_key: OpenAI API key
        pinecone_api_key: Pinecone API key
        pinecone_environment: Pinecone environment
        core_index_name: Core index name
        longtail_index_name: Longtail index name
        
    Returns:
        Initialized RetrievalPipeline
    """
    # Initialize embedding generator
    embedding_generator = EmbeddingGenerator(
        model_name="text-embedding-3-large",
        dimensions=1536,
        api_key=openai_api_key
    )
    
    # Initialize vector stores
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
        core_top_k=12,
        longtail_top_k=6,
        min_score_threshold=0.7,
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
        description="Query the two-tier vector indexes"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Search query"
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
    parser.add_argument(
        "--use-longtail",
        action="store_true",
        help="Also search longtail index"
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
    
    # Initialize pipeline
    print("Initializing retrieval pipeline...")
    retrieval_pipeline = initialize_retrieval_pipeline(
        openai_api_key=openai_key,
        pinecone_api_key=pinecone_key,
        pinecone_environment=pinecone_env,
        core_index_name=args.core_index,
        longtail_index_name=args.longtail_index
    )
    
    # Query
    print(f"\nQuerying: {args.query}")
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
