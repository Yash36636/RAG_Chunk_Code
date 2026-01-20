"""
Confidence Scoring Module
Determines answer authoritativeness based on retrieval quality
"""

from typing import List, Any, Tuple
from dataclasses import dataclass

# Score thresholds (calibrated for sentence-transformers/all-MiniLM-L6-v2)
MIN_SCORE = 0.60  # 60% threshold - only include high-quality sources
HIGH_THRESHOLD = 0.65
MEDIUM_THRESHOLD = 0.52
MAX_SOURCES = 5  # Maximum citations to show


@dataclass
class ConfidenceResult:
    """Result of confidence computation"""
    level: str  # "high" | "medium" | "low"
    avg_score: float
    num_sources: int
    explanation: str


def compute_confidence(results: List[Any]) -> ConfidenceResult:
    """
    Compute confidence level from retrieval results.
    
    Args:
        results: List of retrieval results with .score attribute
        
    Returns:
        ConfidenceResult with level, scores, and explanation
    """
    if not results:
        return ConfidenceResult(
            level="low",
            avg_score=0.0,
            num_sources=0,
            explanation="No relevant sources found"
        )
    
    # Filter by minimum score
    valid_results = [r for r in results if getattr(r, 'score', 0) >= MIN_SCORE]
    
    if not valid_results:
        return ConfidenceResult(
            level="low",
            avg_score=0.0,
            num_sources=0,
            explanation="No sources met relevance threshold"
        )
    
    # Calculate average score
    avg_score = sum(r.score for r in valid_results) / len(valid_results)
    num_sources = len(valid_results)
    
    # Determine confidence level
    if avg_score >= HIGH_THRESHOLD and num_sources >= 2:
        return ConfidenceResult(
            level="high",
            avg_score=round(avg_score, 3),
            num_sources=num_sources,
            explanation=f"Strong grounding: {num_sources} sources, avg score {avg_score:.2f}"
        )
    elif avg_score >= MEDIUM_THRESHOLD:
        return ConfidenceResult(
            level="medium",
            avg_score=round(avg_score, 3),
            num_sources=num_sources,
            explanation=f"Moderate grounding: {num_sources} sources, avg score {avg_score:.2f}"
        )
    else:
        return ConfidenceResult(
            level="low",
            avg_score=round(avg_score, 3),
            num_sources=num_sources,
            explanation=f"Weak grounding: scores below threshold"
        )


def apply_diversity_constraint(results: List[Any], max_sources: int = MAX_SOURCES) -> List[Any]:
    """
    Apply diversity constraint: max one citation per video.
    
    Args:
        results: Filtered retrieval results
        max_sources: Maximum number of sources to return
        
    Returns:
        Deduplicated list of results (one per video)
    """
    final_sources = []
    seen_videos = set()
    
    for r in results:
        video_id = getattr(r, 'video_id', None)
        if video_id and video_id not in seen_videos:
            final_sources.append(r)
            seen_videos.add(video_id)
        if len(final_sources) >= max_sources:
            break
    
    return final_sources


def filter_by_score(results: List[Any], min_score: float = MIN_SCORE) -> List[Any]:
    """
    Filter results by minimum score threshold.
    
    Args:
        results: Raw retrieval results
        min_score: Minimum score threshold
        
    Returns:
        Filtered list of results
    """
    return [r for r in results if getattr(r, 'score', 0) >= min_score]


def get_confidence_prompt_modifier(confidence: str) -> str:
    """
    Get prompt modifier based on confidence level.
    
    Args:
        confidence: "high" | "medium" | "low"
        
    Returns:
        Instruction to add to LLM prompt
    """
    if confidence == "high":
        return """
CONFIDENCE: HIGH
You have strong, relevant sources. Be authoritative and direct.
Cite specific insights from the sources."""
    
    elif confidence == "medium":
        return """
CONFIDENCE: MEDIUM
Sources are relevant but not comprehensive. Be careful and balanced.
Acknowledge where sources are strong vs where you're extrapolating."""
    
    else:  # low
        return """
CONFIDENCE: LOW
Sources are weak or not directly relevant. Do NOT claim authority.
Instead:
1. Acknowledge the question is only loosely related to available sources
2. Reframe toward product management thinking
3. Keep response brief and humble
4. Do NOT invent citations or specific advice"""


def limit_sources_by_answer_length(answer_text: str, sources: list, max_sources: int = MAX_SOURCES) -> list:
    """
    Dynamically limit sources based on answer density.
    
    Rule: Include all sources that passed score threshold (>= 0.60), up to max_sources
    
    Args:
        answer_text: The generated answer text
        sources: List of source items (already filtered by score >= 0.60)
        max_sources: Absolute maximum
        
    Returns:
        Limited list of sources sorted by score descending
    """
    if not sources:
        return []
    
    # Helper to get score from either Pydantic model or dict
    def get_score(s):
        if hasattr(s, 'score'):
            return s.score
        elif isinstance(s, dict):
            return s.get('score', 0)
        return 0
    
    # All sources passed the 60% threshold, so include them (up to max)
    # Sort by score descending to show best sources first
    sorted_sources = sorted(sources, key=get_score, reverse=True)
    
    return sorted_sources[:max_sources]
