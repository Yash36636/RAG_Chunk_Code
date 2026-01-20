"""
Smart Follow-up Question Generator
==================================
Generates contextually relevant, depth-building follow-up questions.

Philosophy:
- Follow-ups must feel like a senior PM mentor pushing deeper thinking
- They must build on what was JUST said, not generic probing
- They must stay on topic (no domain drift)
- They must be answerable with the same/adjacent sources

This is NOT a generic chatbot. This is a PM thinking companion.
"""

from typing import List, Optional
import json
import re


# Production-grade follow-up prompt (CRITICAL)
FOLLOWUP_SYSTEM_PROMPT = """You are a senior product manager helping another PM think deeper.

Your job is to generate 2-3 follow-up questions that:
• Naturally continue the conversation
• Go DEEPER into product management thinking
• Build DIRECTLY on the answer just given
• Feel like a thoughtful PM interviewer or mentor

STRICT RULES:
• Do NOT change the topic
• Do NOT ask generic clarification questions like "What stage is your product?"
• Do NOT repeat the original question
• Do NOT ask questions requiring external knowledge
• Questions must be specific to what was just discussed

The follow-ups should feel like a senior PM pushing deeper thinking, not a support chatbot.

Output ONLY the questions as a JSON array:
["Question 1?", "Question 2?", "Question 3?"]"""


def generate_followups(
    user_query: str,
    answer_text: str,
    source_topics: List[str],
    llm_client,
    confidence: str
) -> List[str]:
    """
    Generate smart, depth-building follow-up questions.
    
    CRITICAL: Only generate if confidence >= medium.
    No generic fallbacks - return empty list if can't generate good questions.
    
    Args:
        user_query: The user's original question
        answer_text: The assistant's answer
        source_topics: Key topics/themes from retrieved sources
        llm_client: LLM client for generation
        confidence: Answer confidence level ("high", "medium", "low")
        
    Returns:
        List of 2-3 follow-up questions, or empty list
    """
    # 🚨 HARD RULE: No follow-ups for low confidence
    # This alone fixes 50% of bad UX
    if confidence == "low":
        return []
    
    # Build rich context for follow-up generation
    # Truncate answer to key points
    answer_summary = answer_text[:400] if len(answer_text) > 400 else answer_text
    
    # Format source themes
    themes_text = ", ".join(source_topics[:5]) if source_topics else "general product management"
    
    user_prompt = f"""User's Question:
{user_query}

Answer Just Given:
{answer_summary}

Key Themes from Sources:
{themes_text}

Generate 2-3 follow-up questions that dig deeper into this specific topic.
Remember: Be like a senior PM mentor pushing for deeper thinking, not a generic chatbot."""

    try:
        response = llm_client.generate_with_system(
            system_prompt=FOLLOWUP_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        # Parse the response
        followups = parse_followup_response(response)
        
        # Validate: must have at least 2 questions
        if followups and len(followups) >= 2:
            # Filter out any generic questions that slipped through
            filtered = filter_generic_questions(followups)
            if len(filtered) >= 2:
                return filtered[:3]
        
    except Exception as e:
        print(f"   [FOLLOWUP] Generation failed: {e}")
    
    # 🚨 NO FALLBACKS - return empty if generation failed
    # Better to show nothing than generic questions
    return []


def parse_followup_response(response: str) -> List[str]:
    """Parse LLM response to extract follow-up questions."""
    # Try JSON parsing first
    try:
        # Find JSON array in response
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        if match:
            questions = json.loads(match.group())
            if isinstance(questions, list):
                return [q.strip() for q in questions if isinstance(q, str) and q.strip()]
    except json.JSONDecodeError:
        pass
    
    # Fallback: extract lines that look like questions
    questions = []
    for line in response.split('\n'):
        line = line.strip()
        if line and '?' in line:
            # Clean up numbering, bullets, quotes
            clean = re.sub(r'^[\d\.\-\*\"\'\[\]]+\s*', '', line)
            clean = clean.strip('"\'[]')
            if len(clean) > 15 and clean.endswith('?'):
                questions.append(clean)
    
    return questions[:3]


def filter_generic_questions(questions: List[str]) -> List[str]:
    """Filter out generic/lazy questions that don't add depth."""
    generic_patterns = [
        r"what stage",
        r"tell me more",
        r"can you clarify",
        r"what (is|are) your",
        r"what do you think",
        r"how does that sound",
        r"does that make sense",
        r"any other questions",
        r"what else",
        r"anything else",
        r"what challenges",
        r"what problems",
        r"what situation",
        r"your product",
        r"your company",
        r"your team",
        r"your experience",
    ]
    
    filtered = []
    for q in questions:
        q_lower = q.lower()
        is_generic = any(re.search(pattern, q_lower) for pattern in generic_patterns)
        if not is_generic:
            filtered.append(q)
    
    return filtered


def extract_source_topics(sources: List[dict]) -> List[str]:
    """
    Extract meaningful topics from source metadata.
    
    Focus on:
    - Speaker names (expertise signals)
    - Key concepts from text
    - Episode themes
    """
    topics = []
    speakers_seen = set()
    
    for source in sources[:5]:
        # Extract speaker name (important for PM context)
        speaker = source.get('speaker', '')
        if speaker and speaker not in speakers_seen and speaker != 'Unknown':
            topics.append(f"{speaker}'s perspective")
            speakers_seen.add(speaker)
        
        # Extract from video title (often contains topic)
        title = source.get('video_title', '')
        if title:
            # Clean up "Episode with X" format
            clean_title = re.sub(r'^Episode with\s+', '', title)
            if clean_title and clean_title not in topics:
                topics.append(clean_title)
        
        # Extract key phrase from text preview
        preview = source.get('text_preview', '')
        if preview and len(preview) > 30:
            # Get first meaningful phrase
            first_part = preview.split('.')[0].strip()
            if len(first_part) > 20 and len(first_part) < 100:
                topics.append(first_part)
    
    # Deduplicate and limit
    seen = set()
    unique_topics = []
    for t in topics:
        t_lower = t.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            unique_topics.append(t)
    
    return unique_topics[:5]


# Memory summarization prompt
MEMORY_SUMMARY_PROMPT = """Summarize this PM conversation for continuity.

Extract:
- Product topics discussed (prioritization, growth, metrics, etc.)
- Frameworks or models mentioned
- Key recommendations given
- User's apparent goal

Rules:
- Ignore casual greetings
- Focus only on product management content
- Keep under 80 words
- Be concise and factual"""


def summarize_memory(
    previous_summary: str,
    recent_turns: str,
    llm_client
) -> str:
    """
    Summarize conversation memory with PM focus.
    
    Args:
        previous_summary: Existing memory summary
        recent_turns: Recent conversation turns
        llm_client: LLM client for summarization
        
    Returns:
        New condensed summary
    """
    context = ""
    if previous_summary:
        context = f"Previous summary: {previous_summary}\n\nNew turns:\n{recent_turns}"
    else:
        context = recent_turns
    
    try:
        summary = llm_client.generate_with_system(
            system_prompt=MEMORY_SUMMARY_PROMPT,
            user_prompt=f"Conversation:\n{context}\n\nSummary:"
        )
        return summary.strip()[:400]  # Cap length
    except Exception as e:
        print(f"   [MEMORY] Summarization failed: {e}")
        return previous_summary  # Keep old summary on failure
