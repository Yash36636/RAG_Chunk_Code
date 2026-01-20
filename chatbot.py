"""
RAG Chatbot - Complete Pipeline
Combines retrieval + answer synthesis for end-to-end chatbot
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Set environment variables
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src import (
    RetrievalPipeline,
    TwoTierEmbeddingPipeline,
    AnswerSynthesizer,
    FreeEmbeddingGenerator,
    FAISSStore,
    ParentChunkLoader
)


def initialize_chatbot(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    device: Optional[str] = None,
    core_index_path: str = "./faiss_indexes/product-management-core",
    longtail_index_path: str = "./faiss_indexes/product-management-longtail",
    llm_provider: str = "openai",
    llm_api_key: Optional[str] = None
):
    """
    Initialize complete chatbot pipeline.
    
    Args:
        model_name: Embedding model name
        device: Device for embeddings
        core_index_path: Path to core FAISS index
        longtail_index_path: Path to longtail FAISS index
        llm_provider: "openai", "anthropic", or "local"
        llm_api_key: API key for LLM provider
        
    Returns:
        Tuple of (retrieval_pipeline, answer_synthesizer)
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
    
    # Initialize retrieval pipeline (with improved settings)
    retrieval_pipeline = RetrievalPipeline(
        embedding_generator=embedding_generator,
        core_store=core_store,
        longtail_store=longtail_store,
        two_tier_pipeline=two_tier_pipeline,
        core_top_k=20,  # STEP 2.2: Increased for better recall
        longtail_top_k=10,
        min_score_threshold=0.3,
        parent_expansion_percent=0.25
    )
    
    # Initialize answer synthesizer
    answer_synthesizer = AnswerSynthesizer(
        llm_provider=llm_provider,
        api_key=llm_api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    )
    
    return retrieval_pipeline, answer_synthesizer


def chat(
    query: str,
    retrieval_pipeline: RetrievalPipeline,
    answer_synthesizer: AnswerSynthesizer,
    parent_loader: Optional[ParentChunkLoader] = None,
    use_longtail: bool = False,
    include_citations: bool = True
) -> dict:
    """
    Complete chat pipeline: retrieve + synthesize.
    
    STEP 1 + 2: Uses semantic deduplication and full parent expansion.
    
    Args:
        query: User question
        retrieval_pipeline: Initialized retrieval pipeline
        answer_synthesizer: Initialized answer synthesizer
        parent_loader: Optional parent chunk loader for full parent expansion
        use_longtail: Whether to search longtail index
        include_citations: Whether to include citations
        
    Returns:
        Dictionary with answer, citations, and sources
    """
    print(f"\nQuery: {query}")
    print("Retrieving relevant chunks...")
    
    # STEP 1 + 2 + 3: Retrieve with deduplication, parent expansion, and query rewriting
    if parent_loader:
        # Use parent loader for full parent expansion
        retrieved_chunks = retrieval_pipeline.retrieve_with_parent_loader(
            query=query,
            parent_loader=parent_loader,
            use_longtail=use_longtail,
            use_query_rewriting=True  # STEP 3: Query rewriting enabled
        )
    else:
        # Fallback: standard retrieve
        retrieved_chunks = retrieval_pipeline.retrieve(
            query=query,
            use_longtail=use_longtail,
            use_query_rewriting=True
        )
    
    print(f"Found {len(retrieved_chunks)} relevant chunks (after deduplication)")
    
    if not retrieved_chunks:
        return {
            'answer': "I couldn't find relevant information to answer your question. Try rephrasing or asking about a different topic.",
            'citations': [],
            'sources': [],
            'num_chunks_used': 0
        }
    
    print("Synthesizing answer...")
    print(f"Using top {min(5, len(retrieved_chunks))} parent contexts for synthesis...")
    
    # STEP 3: Synthesize answer (with compression)
    result = answer_synthesizer.synthesize(
        query=query,
        retrieved_chunks=retrieved_chunks,
        include_citations=include_citations,
        top_k=5  # STEP 3A: Max 5 parents
    )
    
    return result


def format_answer(result: dict) -> str:
    """Format answer with citations for display."""
    lines = []
    
    lines.append("="*70)
    lines.append("ANSWER")
    lines.append("="*70)
    lines.append(f"\n{result['answer']}\n")
    
    if result.get('citations'):
        lines.append("\n" + "="*70)
        lines.append("CITATIONS")
        lines.append("="*70)
        for i, citation in enumerate(result['citations'][:5], 1):  # Top 5 citations
            lines.append(f"\n[{i}] {citation['text']}")
            lines.append(f"    {citation['speaker'] or 'Unknown'} - {citation['timestamp']}")
            lines.append(f"    {citation['youtube_url']}")
    
    if result.get('sources'):
        lines.append("\n" + "="*70)
        lines.append("SOURCES")
        lines.append("="*70)
        for source in result['sources'][:3]:  # Top 3 sources
            lines.append(f"  - {source['youtube_url']}")
    
    lines.append("\n" + "="*70)
    
    return "\n".join(lines)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="RAG Chatbot - Ask questions about product management podcasts"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Your question"
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model name"
    )
    parser.add_argument(
        "--llm-provider",
        type=str,
        choices=["openai", "anthropic", "local"],
        default="openai",
        help="LLM provider for answer synthesis"
    )
    parser.add_argument(
        "--llm-api-key",
        type=str,
        help="API key for LLM provider (or set OPENAI_API_KEY/ANTHROPIC_API_KEY env var)"
    )
    parser.add_argument(
        "--no-citations",
        action="store_true",
        help="Don't include citations in answer"
    )
    parser.add_argument(
        "--use-longtail",
        action="store_true",
        help="Also search longtail index"
    )
    
    args = parser.parse_args()
    
    # Initialize chatbot
    print("Initializing chatbot...")
    retrieval_pipeline, answer_synthesizer = initialize_chatbot(
        model_name=args.embedding_model,
        llm_provider=args.llm_provider,
        llm_api_key=args.llm_api_key
    )
    
    # STEP 2: Load parent chunks for full expansion
    print("Loading parent chunks...")
    parent_loader = ParentChunkLoader(chunks_dir="chunks_product_management")
    print(f"Loaded {parent_loader.get_stats()['total_parents']} parent chunks")
    
    # Chat
    result = chat(
        query=args.query,
        retrieval_pipeline=retrieval_pipeline,
        answer_synthesizer=answer_synthesizer,
        parent_loader=parent_loader,  # STEP 2: Pass parent loader
        use_longtail=args.use_longtail,
        include_citations=not args.no_citations
    )
    
    # Display
    print(format_answer(result))
    
    return result


if __name__ == "__main__":
    main()
