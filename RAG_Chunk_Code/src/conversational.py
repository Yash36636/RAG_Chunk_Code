"""
Conversational PM Module - Friendly mentor-style responses
Used when RAG confidence is low or query is casual
"""

from typing import Dict, Any, Optional
from .prompts import load_prompt
from .llm import get_llm


def conversational_pm_answer(
    query: str, 
    llm_client=None,
    conversation_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a conversational PM mentor response.
    
    Used when:
    - RAG retrieval confidence is low
    - Query is casual/not PM-specific
    - Need friendly fallback without citations
    
    Args:
        query: User's question
        llm_client: Optional LLM client (will create one if not provided)
        conversation_context: Previous conversation turns for continuity
        
    Returns:
        Response dict with mode="conversation"
    """
    # Load conversational prompt
    system_prompt = load_prompt("conversational_pm.txt")
    
    # Get or create LLM client
    if llm_client is None:
        llm_client = get_llm("auto")
    
    # Build the user prompt with conversation context
    if conversation_context:
        user_prompt = f"""Previous conversation:
{conversation_context}

Current question: {query}

Continue the conversation as a friendly PM mentor. Build on previous context where relevant.
Be helpful, practical, and conversational. Guide toward product management thinking."""
    else:
        user_prompt = f"""Question: {query}

Respond as a friendly PM mentor. Be helpful, practical, and conversational."""

    try:
        # Generate response
        response = llm_client.generate_with_system(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "mode": "conversation",
            "answer": response,
            "citations": [],
            "confidence": None
        }
        
    except Exception as e:
        # Graceful fallback
        return {
            "mode": "conversation",
            "answer": (
                "That's a great question! While I'd love to dive deeper, "
                "could you tell me a bit more about your specific situation? "
                "For example, are you working on a B2B or B2C product? "
                "What stage is your product at?"
            ),
            "citations": [],
            "confidence": None
        }
