"""
Query Router - Determines whether to use RAG or conversational mode
Production-grade with PM intent detection and confidence thresholds
"""

from typing import List, Any

# PM-related keywords for intent detection
PM_KEYWORDS = {
    "product", "pm", "features", "prioritize", "roadmap",
    "users", "growth", "metrics", "revenue", "pricing",
    "retention", "activation", "strategy", "okr", "kpi",
    "sprint", "agile", "backlog", "stakeholder", "mvp",
    "user research", "customer", "feedback", "iteration",
    "launch", "release", "a/b test", "experiment", "hypothesis",
    "market", "competitor", "positioning", "segmentation",
    "onboarding", "churn", "engagement", "conversion",
    "funnel", "journey", "persona", "jobs to be done",
    "discovery", "delivery", "outcome", "output", "impact",
    "prioritization", "framework", "rice", "ice", "moscow",
    "north star", "leading indicator", "lagging indicator"
}


def is_pm_intent(query: str) -> bool:
    """
    Detect if query has product management intent.
    
    Args:
        query: User's question
        
    Returns:
        True if query appears to be PM-related
    """
    q = query.lower()
    return any(keyword in q for keyword in PM_KEYWORDS)


def should_use_rag(results: List[Any], min_strong_hits: int = 2, score_threshold: float = 0.55) -> bool:
    """
    Determine if RAG retrieval results are strong enough to use.
    
    Args:
        results: Retrieved chunks with scores
        min_strong_hits: Minimum number of high-confidence results needed
        score_threshold: Minimum score to consider a "strong" hit
        
    Returns:
        True if we have enough strong evidence to use RAG mode
    """
    if not results:
        return False
    
    # Count chunks with strong relevance scores
    strong_hits = [r for r in results if getattr(r, 'score', 0) >= score_threshold]
    
    return len(strong_hits) >= min_strong_hits


def get_query_mode(query: str, results: List[Any]) -> str:
    """
    Determine the appropriate response mode.
    
    Args:
        query: User's question
        results: Retrieved chunks
        
    Returns:
        "rag" | "conversation"
    """
    if is_pm_intent(query) and should_use_rag(results):
        return "rag"
    return "conversation"
