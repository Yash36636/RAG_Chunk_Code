"""
Unified Answer Synthesizer
Production-grade with context control, confidence scoring, and multi-provider support

PROMPT CACHING:
- System prompt is STATIC (imported from cached_system.py)
- Groq optimizes for repeated system prompts
- User prompt is dynamic (query, sources, memory)
"""

from typing import List, Dict, Any, Optional, Iterator
from .retrieval import RetrievalResult
from .llm.base import BaseLLM

# Import cached system prompt (STATIC - enables Groq prompt caching)
try:
    from .prompts.cached_system import CACHED_SYSTEM_PROMPT
except ImportError:
    CACHED_SYSTEM_PROMPT = None


class UnifiedSynthesizer:
    """
    Production-grade answer synthesizer.
    
    Features:
    - Multi-provider LLM support (Groq, Ollama, Gemini)
    - Hard context limits (cannot be bypassed)
    - Confidence scoring
    - Fast vs Deep modes
    - Streaming support
    """
    
    # Global context limits (CANNOT be overridden)
    MAX_CHUNKS_FAST = 5  # Match MAX_SOURCES - include all sources with score >= 0.60
    MAX_CHUNKS_DEEP = 5
    MAX_CHARS_PER_CHUNK = 600  # Slightly shorter to fit more sources
    
    # System prompt for RAG - use cached version if available, otherwise fallback
    # NOTE: This should be IDENTICAL across all requests to enable Groq prompt caching
    SYSTEM_PROMPT = CACHED_SYSTEM_PROMPT or """You are Product Wisdom Hub — a senior product management advisor.

ABSOLUTE RULES (NEVER VIOLATE):
1. You MUST use the EXACT output format below
2. You MUST NOT use markdown (no ###, no **, no -)
3. You MUST NOT use numbered lists in Key Ideas
4. You MUST keep each section concise
5. Follow-up questions use the SAME format as initial questions

OUTPUT FORMAT (MANDATORY - USE EXACTLY):

Direct Answer
[1 short paragraph, 2-3 sentences max]

Key Ideas
• [insight 1 - one line]
• [insight 2 - one line]  
• [insight 3 - one line]

Common Pitfall
[1 sentence only]

Summary
[1 sentence only]

CITATION RULES:
• Reference speakers by name: "According to [Speaker Name]..."
• Add [SOURCE X] after claims that come from sources
• Never invent citations or speakers

SOURCE GROUNDING:
• Use ONLY information from provided sources
• If sources are weak, say "Based on limited sources..."
• Never hallucinate advice without grounding

STYLE:
• Be opinionated, not wishy-washy
• Be practical, not academic  
• Be concise, not verbose
• Use bullets (•) not dashes (-)
• NO markdown formatting ever"""
    
    # Refusal phrases to detect safety responses
    REFUSAL_PHRASES = [
        "i cannot provide",
        "i can't help with",
        "i'm unable to assist",
        "cannot help with that",
        "i cannot assist",
        "i'm not able to",
        "i can't assist",
        "i cannot answer",
        "against my guidelines",
        "i'm sorry, but i can't",
        "i apologize, but i cannot",
        "not able to provide",
        "i can't provide",
        "unable to help"
    ]
    
    @staticmethod
    def _is_refusal(answer: str) -> bool:
        """
        Detect if LLM gave a refusal/safety response.
        If so, we should NOT show citations (they're irrelevant).
        
        This matches behavior of ChatGPT, Perplexity, and Google.
        """
        answer_lower = answer.lower()
        return any(phrase in answer_lower for phrase in UnifiedSynthesizer.REFUSAL_PHRASES)
    
    def __init__(
        self,
        llm_client: BaseLLM,
        mode: str = "fast"
    ):
        """
        Initialize synthesizer.
        
        Args:
            llm_client: LLM instance (Groq, Ollama, etc.)
            mode: "fast" or "deep"
        """
        self.llm = llm_client
        self.mode = mode
        self.provider = llm_client.get_provider_name()
        
        print(f"   [OK] Synthesizer ready (provider: {self.provider}, mode: {mode})")
    
    def _compute_confidence(self, chunks: List[RetrievalResult]) -> str:
        """
        Compute confidence level based on retrieval scores.
        
        Returns: "high", "medium", or "low"
        """
        if not chunks:
            return "low"
        
        avg_score = sum(c.score for c in chunks) / len(chunks)
        
        if avg_score > 0.6:
            return "high"
        elif avg_score > 0.45:
            return "medium"
        else:
            return "low"
    
    def _enforce_context_limits(
        self,
        chunks: List[RetrievalResult],
        max_chunks: int
    ) -> List[RetrievalResult]:
        """
        Enforce hard limits on context size.
        This CANNOT be overridden - global safety mechanism.
        """
        # Deduplicate by parent_id
        seen = set()
        unique = []
        for chunk in chunks:
            parent_id = chunk.parent_id or chunk.chunk_id
            if parent_id not in seen:
                unique.append(chunk)
                seen.add(parent_id)
        
        # Hard limit on number of chunks
        limited = unique[:max_chunks]
        
        # Truncate each chunk's text
        for chunk in limited:
            text = chunk.parent_text if chunk.parent_text else chunk.text
            if len(text) > self.MAX_CHARS_PER_CHUNK:
                truncated = text[:self.MAX_CHARS_PER_CHUNK]
                last_period = truncated.rfind('.')
                if last_period > self.MAX_CHARS_PER_CHUNK * 0.8:
                    truncated = truncated[:last_period + 1]
                chunk.parent_text = truncated + "..."
        
        print(f"   [CONTEXT] Using {len(limited)} chunks (max: {max_chunks})")
        
        return limited
    
    def _get_source_weight(self, score: float) -> str:
        """Determine source weight based on FAISS score."""
        if score >= 0.70:
            return "HIGH"
        elif score >= 0.55:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _build_context_blocks(self, chunks: List[RetrievalResult]) -> str:
        """
        Build weighted context blocks with SOURCE numbers for citation.
        Sources are explicitly weighted (HIGH/MEDIUM/LOW) for the LLM.
        """
        blocks = []
        
        for i, chunk in enumerate(chunks, 1):
            # Get metadata for citations
            speaker = chunk.get_speaker() if hasattr(chunk, 'get_speaker') else (chunk.speaker or chunk.guest or 'Unknown')
            timestamp = chunk.get_timestamp_str() if hasattr(chunk, 'get_timestamp_str') else f"{int(chunk.start_seconds // 60)}m{int(chunk.start_seconds % 60)}s"
            video_title = getattr(chunk, 'video_title', '') or f"Episode {chunk.video_id}"
            
            # Determine source weight
            weight = self._get_source_weight(chunk.score)
            
            text = chunk.parent_text if chunk.parent_text else chunk.text
            
            # Truncate text if needed
            if len(text) > self.MAX_CHARS_PER_CHUNK:
                truncated = text[:self.MAX_CHARS_PER_CHUNK]
                last_period = truncated.rfind('.')
                if last_period > self.MAX_CHARS_PER_CHUNK * 0.8:
                    truncated = truncated[:last_period + 1]
                text = truncated + "..."
            
            block = f"""SOURCE [{i}] - Confidence: {weight}
Speaker: {speaker}
Video: {video_title}
Timestamp: {timestamp}
Excerpt:
{text}
"""
            blocks.append(block)
        
        return "\n\n".join(blocks)
    
    def _build_prompt(
        self, 
        context: str, 
        query: str, 
        confidence: str,
        conversation_context: Optional[str] = None,
        summary_memory: Optional[str] = None,
        recent_turns: Optional[str] = None
    ) -> str:
        """
        Build complete prompt with proper assembly order for caching.
        
        ASSEMBLY ORDER (CRITICAL for prompt caching):
        1. [SUMMARY MEMORY]  ← compressed earlier conversation
        2. [RAG CONTEXT]     ← FAISS results
        3. [RECENT TURNS]    ← last 2 turns
        4. [USER QUERY]
        
        Note: System prompt is handled separately (static, cached by Groq)
        """
        confidence_note = {
            "high": "Sources are strong and directly relevant. Be authoritative.",
            "medium": "Sources are relevant but not comprehensive. Be balanced.",
            "low": "Sources are weak. Acknowledge limitations and be concise."
        }
        
        sections = []
        
        # 1. Summary Memory (compressed earlier conversation)
        if summary_memory:
            sections.append(f"""CONVERSATION SUMMARY (earlier discussion):
{summary_memory}

Note: This is background only. All facts must come from VERIFIED SOURCES.""")
        
        # 2. RAG Context (retrieved sources)
        sections.append(f"""VERIFIED SOURCES (grounded excerpts from expert PM conversations):

{context}""")
        
        # 3. Recent Turns (last 2 turns for immediate context)
        if recent_turns:
            sections.append(f"""RECENT CONVERSATION:
{recent_turns}""")
        elif conversation_context:
            # Backward compatibility with old format
            sections.append(f"""CONVERSATION CONTEXT (for continuity only, NOT ground truth):
{conversation_context}

Note: Use conversation history ONLY for understanding what was discussed. 
All factual claims must come from the VERIFIED SOURCES above.""")
        
        # 4. User Query + Task (reinforce strict format)
        sections.append(f"""USER QUESTION:
{query}

CONFIDENCE LEVEL: {confidence.upper()}
{confidence_note[confidence]}

RESPOND USING THIS EXACT FORMAT (no markdown, no headers with #):

Direct Answer
[your 2-3 sentence answer here]

Key Ideas
• [bullet 1]
• [bullet 2]
• [bullet 3]

Common Pitfall
[one sentence]

Summary
[one sentence]""")
        
        return "\n\n---\n\n".join(sections)
    
    def synthesize(
        self,
        query: str,
        retrieved_chunks: List[RetrievalResult],
        include_citations: bool = True,
        mode: Optional[str] = None,
        conversation_context: Optional[str] = None,
        summary_memory: Optional[str] = None,
        recent_turns: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize answer using configured LLM backend.
        
        PROMPT CACHING:
        - System prompt is STATIC (cached by Groq after first request)
        - User prompt is DYNAMIC (query, sources, memory)
        
        Args:
            query: User's question
            retrieved_chunks: List of retrieved chunks
            include_citations: Whether to include citations
            mode: Override mode ("fast" or "deep")
            conversation_context: Previous conversation turns (legacy format)
            summary_memory: Compressed earlier conversation summary
            recent_turns: Last 2 conversation turns
            
        Returns:
            Dictionary with answer, citations, confidence, etc.
        """
        if not retrieved_chunks:
            return {
                'answer': "I couldn't find relevant information to answer your question.",
                'citations': [],
                'sources': [],
                'num_chunks_used': 0,
                'confidence': 'low',
                'provider': self.provider,
                'mode': mode or self.mode
            }
        
        # Determine mode limits
        active_mode = mode or self.mode
        max_chunks = self.MAX_CHUNKS_FAST if active_mode == "fast" else self.MAX_CHUNKS_DEEP
        
        # Enforce context limits
        top_chunks = self._enforce_context_limits(retrieved_chunks, max_chunks)
        
        # Compute confidence
        confidence = self._compute_confidence(top_chunks)
        print(f"   [CONFIDENCE] {confidence.upper()}")
        
        # Build prompt with proper assembly order for caching
        context = self._build_context_blocks(top_chunks)
        prompt = self._build_prompt(
            context=context, 
            query=query, 
            confidence=confidence, 
            conversation_context=conversation_context,
            summary_memory=summary_memory,
            recent_turns=recent_turns
        )
        
        # Generate answer using PROPER system prompt
        try:
            answer = self.llm.generate_with_system(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=prompt
            )
        except Exception as e:
            print(f"   [ERROR] LLM generation failed: {e}")
            return {
                'answer': f"Error generating answer: {str(e)[:100]}",
                'citations': [],
                'sources': [],
                'num_chunks_used': len(top_chunks),
                'confidence': confidence,
                'provider': self.provider,
                'mode': active_mode
            }
        
        # SAFETY CHECK: Detect refusals - don't show citations for refused questions
        is_refusal = self._is_refusal(answer)
        if is_refusal:
            print("   [SAFETY] Refusal detected - hiding citations")
            confidence = "low"  # Override confidence for refusals
        
        # Build GROUND-TRUTH citations (no hallucination possible)
        # BUT: Skip if LLM refused (citations would be irrelevant)
        citations = []
        sources = []
        
        if include_citations and not is_refusal:
            for i, chunk in enumerate(top_chunks, 1):
                # Use helper methods if available, otherwise compute directly
                speaker = chunk.get_speaker() if hasattr(chunk, 'get_speaker') else (chunk.speaker or getattr(chunk, 'guest', None) or 'Unknown')
                timestamp_str = chunk.get_timestamp_str() if hasattr(chunk, 'get_timestamp_str') else f"{int(chunk.start_seconds // 60)}m{int(chunk.start_seconds % 60)}s"
                youtube_url = chunk.get_youtube_url() if hasattr(chunk, 'get_youtube_url') else f"https://www.youtube.com/watch?v={chunk.video_id}&t={int(chunk.start_seconds)}s"
                video_title = getattr(chunk, 'video_title', '') or f"Episode {chunk.video_id}"
                
                citations.append({
                    'source_num': i,  # Matches [SOURCE X] in answer
                    'speaker': speaker,
                    'video_title': video_title,
                    'timestamp': timestamp_str,
                    'youtube_url': youtube_url,
                    'video_id': chunk.video_id,
                    'text_preview': chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text
                })
                
                source = {'video_id': chunk.video_id, 'youtube_url': youtube_url, 'video_title': video_title}
                if source not in sources:
                    sources.append(source)
        
        return {
            'answer': answer,
            'citations': citations,
            'sources': sources,
            'num_chunks_used': len(top_chunks),
            'confidence': confidence,
            'provider': self.provider,
            'mode': active_mode,
            'is_refusal': is_refusal
        }
