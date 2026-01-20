"""
Safety Module - Detects harmful queries and provides appropriate responses
Production-grade with clear boundaries
"""

# Self-harm related terms (handle with care)
SELF_HARM_TERMS = {
    "kill myself", "suicide", "end my life", "want to die",
    "don't want to live", "better off dead", "hurt myself",
    "self harm", "suicidal"
}

# General harmful/inappropriate terms
HARMFUL_TERMS = {
    "how to hack", "how to steal", "illegal", "exploit vulnerability",
    "bypass security", "credit card fraud"
}

# Safety response message
SAFETY_RESPONSE = (
    "I can't help with that, but you don't have to handle things alone. "
    "If this is serious, please consider reaching out to someone you trust "
    "or a professional resource in your area.\n\n"
    "**Crisis Resources:**\n"
    "- National Suicide Prevention Lifeline: 988 (US)\n"
    "- Crisis Text Line: Text HOME to 741741\n"
    "- International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/"
)

# Redirect response for off-topic harmful queries
REDIRECT_RESPONSE = (
    "I'm designed to help with product management questions. "
    "I can't assist with that request, but I'd be happy to help you with "
    "topics like prioritization, growth strategy, user research, or product leadership."
)


def is_self_harm(query: str) -> bool:
    """
    Detect if query contains self-harm related content.
    
    Args:
        query: User's question
        
    Returns:
        True if self-harm content detected
    """
    q = query.lower()
    return any(term in q for term in SELF_HARM_TERMS)


def is_harmful(query: str) -> bool:
    """
    Detect if query contains general harmful content.
    
    Args:
        query: User's question
        
    Returns:
        True if harmful content detected
    """
    q = query.lower()
    return any(term in q for term in HARMFUL_TERMS)


def get_safety_response(query: str) -> dict | None:
    """
    Check query for safety concerns and return appropriate response.
    
    Args:
        query: User's question
        
    Returns:
        Safety response dict if blocked, None if safe
    """
    if is_self_harm(query):
        return {
            "mode": "safety",
            "answer": SAFETY_RESPONSE,
            "citations": [],
            "confidence": None
        }
    
    if is_harmful(query):
        return {
            "mode": "safety", 
            "answer": REDIRECT_RESPONSE,
            "citations": [],
            "confidence": None
        }
    
    return None
