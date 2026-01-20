"""
Query Rewriter Module
STEP 3: Generate query variants to improve recall
"""

from typing import List


class QueryRewriter:
    """
    Rewrites queries into multiple variants for better retrieval.
    
    This improves recall without touching embeddings.
    """
    
    def __init__(self):
        """Initialize query rewriter."""
        pass
    
    def rewrite(self, query: str) -> List[str]:
        """
        Generate query variants.
        
        Args:
            query: Original user query
            
        Returns:
            List of query variants (including original)
        """
        variants = [query]  # Always include original
        
        query_lower = query.lower()
        
        # Pattern 1: Add "product manager" context if not present
        if "product manager" not in query_lower and "pm" not in query_lower:
            if query_lower.startswith("how to"):
                variants.append(f"how do product managers {query_lower[7:]}")
            elif query_lower.startswith("what is"):
                variants.append(f"what is product management {query_lower[7:]}")
        
        # Pattern 2: Add framework/approach context
        if "framework" not in query_lower and "approach" not in query_lower:
            if "how to" in query_lower or "how do" in query_lower:
                variants.append(f"framework for {query_lower}")
                variants.append(f"approach to {query_lower}")
        
        # Pattern 3: Add "leaders" or "experts" context
        if "leader" not in query_lower and "expert" not in query_lower:
            variants.append(f"how do leaders {query_lower[7:]}" if query_lower.startswith("how to") else query)
        
        # Pattern 4: Remove question mark and add variations
        if query.endswith("?"):
            base = query[:-1].strip()
            variants.append(base)
            variants.append(f"{base} in product management")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            variant_lower = variant.lower().strip()
            if variant_lower not in seen:
                seen.add(variant_lower)
                unique_variants.append(variant)
        
        return unique_variants[:5]  # Limit to 5 variants max
