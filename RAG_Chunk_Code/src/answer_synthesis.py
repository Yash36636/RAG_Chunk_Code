"""
Answer Synthesis Module
STEP 3: Generate coherent answers from retrieved chunks using LLM
Implements: Top-K selection, per-parent compression, final synthesis
"""

from typing import List, Dict, Optional, Any
from .retrieval import RetrievalResult


# STEP 3B: Compression prompt (LOCKED)
COMPRESSION_PROMPT = """You are given a podcast transcript excerpt.

Extract ONLY:
1. The core idea or principle
2. Any concrete advice or heuristic
3. One short supporting example (if present)

Rules:
- Be concise
- Do NOT add new ideas
- Do NOT generalize beyond the text
- Use bullet points
"""


class AnswerSynthesizer:
    """
    Synthesizes answers from retrieved chunks using LLM.
    
    STEP 3 Implementation:
    - Top-K parent selection (max 5)
    - Per-parent compression
    - Final answer synthesis with citations
    """
    
    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None):
        """
        Initialize answer synthesizer.
        
        Args:
            llm_provider: "openai", "anthropic", or "local"
            api_key: API key for cloud providers
        """
        self.llm_provider = llm_provider
        self.api_key = api_key
        
        if llm_provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key) if api_key else None
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        elif llm_provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
            except ImportError:
                raise ImportError("anthropic package required. Install with: pip install anthropic")
        else:
            self.client = None
    
    def synthesize(
        self,
        query: str,
        retrieved_chunks: List[RetrievalResult],
        include_citations: bool = True,
        top_k: int = 5  # STEP 3A: Max 5 parents
    ) -> Dict[str, Any]:
        """
        STEP 3: Complete synthesis pipeline.
        
        Args:
            query: User's question
            retrieved_chunks: List of retrieved chunks with parent context
            include_citations: Whether to include timestamp citations
            top_k: Maximum number of parent contexts to use (default: 5)
            
        Returns:
            Dictionary with 'answer', 'citations', and 'sources'
        """
        if not retrieved_chunks:
            return {
                'answer': "I couldn't find relevant information to answer your question. Try rephrasing or asking about a different topic.",
                'citations': [],
                'sources': [],
                'num_chunks_used': 0
            }
        
        # STEP 3A: Select top-K parents
        top_parents = self._select_top_k_parents(retrieved_chunks, k=top_k)
        
        # STEP 3B: Compress each parent
        compressed_parents = self._compress_parents(top_parents)
        
        # STEP 3C: Final answer synthesis
        final_answer = self._synthesize_answer(query, compressed_parents)
        
        # Extract citations
        citations = self._extract_citations_from_compressed(compressed_parents) if include_citations else []
        
        # Extract sources
        sources = self._extract_sources_from_compressed(compressed_parents)
        
        return {
            'answer': final_answer,
            'citations': citations,
            'sources': sources,
            'num_chunks_used': len(top_parents),
            'compressed_parents': compressed_parents  # For debugging
        }
    
    def _select_top_k_parents(
        self,
        chunks: List[RetrievalResult],
        k: int = 5
    ) -> List[RetrievalResult]:
        """
        STEP 3A: Select top-K parent contexts by similarity score.
        
        Rule: Max 5 parent contexts go to the LLM.
        """
        # Sort by score (descending) and take top K
        sorted_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)
        return sorted_chunks[:k]
    
    def _compress_parents(
        self,
        parents: List[RetrievalResult]
    ) -> List[Dict[str, Any]]:
        """
        STEP 3B: Compress each parent independently.
        
        Each parent is compressed to ~150-250 tokens.
        """
        compressed = []
        
        for parent in parents:
            # Use parent text if available, otherwise child text
            context_text = parent.parent_text if parent.parent_text else parent.text
            
            # Compress using LLM
            compressed_text = self._compress_single_parent(context_text)
            
            # Format timestamp
            minutes = int(parent.start_seconds // 60)
            seconds = int(parent.start_seconds % 60)
            timestamp = f"{minutes}m{seconds}s"
            
            compressed.append({
                "video_id": parent.video_id,
                "parent_id": parent.parent_id,
                "timestamp_seconds": parent.start_seconds,
                "timestamp": timestamp,
                "youtube_url": self._create_youtube_url(parent.video_id, parent.start_seconds),
                "speaker": parent.speaker,
                "score": parent.score,
                "compressed_text": compressed_text
            })
        
        return compressed
    
    def _compress_single_parent(self, context_text: str) -> str:
        """
        Compress a single parent context using LLM.
        
        Returns concise summary (~150-250 tokens).
        """
        prompt = f"""{COMPRESSION_PROMPT}

Transcript:
{context_text}
"""
        
        if self.llm_provider == "openai":
            return self._call_openai(prompt, max_tokens=300, temperature=0.2)
        elif self.llm_provider == "anthropic":
            return self._call_anthropic(prompt, max_tokens=300, temperature=0.2)
        else:
            # Fallback: simple truncation
            return context_text[:500] + "..." if len(context_text) > 500 else context_text
    
    def _synthesize_answer(
        self,
        query: str,
        compressed_parents: List[Dict[str, Any]]
    ) -> str:
        """
        STEP 3C: Final answer synthesis.
        
        Synthesizes one clean answer from compressed parent contexts.
        """
        prompt = self._build_synthesis_prompt(query, compressed_parents)
        
        if self.llm_provider == "openai":
            return self._call_openai(prompt, max_tokens=1000, temperature=0.3)
        elif self.llm_provider == "anthropic":
            return self._call_anthropic(prompt, max_tokens=1000, temperature=0.3)
        else:
            # Fallback: simple concatenation
            return self._simple_synthesis_fallback(query, compressed_parents)
    
    def _build_synthesis_prompt(
        self,
        query: str,
        compressed_parents: List[Dict[str, Any]]
    ) -> str:
        """
        Build final synthesis prompt.
        
        Instructions:
        - Synthesize ideas, do NOT list sources separately
        - Group similar ideas together
        - Be practical and opinionated
        - Use bullet points
        - After each bullet, add the source reference in parentheses
        - Do NOT hallucinate or add external knowledge
        """
        sources_text = ""
        
        for i, p in enumerate(compressed_parents, 1):
            speaker_info = f" ({p['speaker']})" if p.get('speaker') else ""
            sources_text += f"""
SOURCE {i}:
{p['compressed_text']}
Reference: {p['youtube_url']} - {p['timestamp']}{speaker_info}
"""
        
        prompt = f"""You are answering the question:

"{query}"

Use ONLY the sources below.

Instructions:
- Synthesize ideas, do NOT list sources separately
- Group similar ideas together
- Be practical and opinionated
- Use bullet points
- After each bullet, add the source reference in parentheses (format: Speaker Name – Timestamp)
- Do NOT hallucinate or add external knowledge
- If sources contradict, acknowledge both perspectives

Sources:
{sources_text}

Final Answer:
"""
        
        return prompt
    
    def _call_openai(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.3
    ) -> str:
        """Call OpenAI API."""
        if not self.client:
            raise ValueError("OpenAI client not initialized. Provide API key.")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective, good quality
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that synthesizes information from podcast transcripts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")
    
    def _call_anthropic(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.3
    ) -> str:
        """Call Anthropic Claude API."""
        if not self.client:
            raise ValueError("Anthropic client not initialized. Provide API key.")
        
        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Fast and cost-effective
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text.strip()
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")
    
    def _simple_synthesis_fallback(
        self,
        query: str,
        compressed_parents: List[Dict[str, Any]]
    ) -> str:
        """
        Simple synthesis without LLM (for testing).
        """
        if not compressed_parents:
            return "No relevant information found."
        
        parts = [f"Based on the podcast transcripts:\n"]
        
        for i, p in enumerate(compressed_parents, 1):
            speaker_info = f" ({p.get('speaker', 'Unknown')})" if p.get('speaker') else ""
            parts.append(f"• {p['compressed_text']}{speaker_info} – {p['timestamp']}")
        
        return "\n".join(parts)
    
    def _extract_citations_from_compressed(
        self,
        compressed_parents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract citation information from compressed parents."""
        citations = []
        
        for p in compressed_parents:
            citation = {
                'text': p['compressed_text'][:150] + "..." if len(p['compressed_text']) > 150 else p['compressed_text'],
                'video_id': p['video_id'],
                'timestamp': p['timestamp'],
                'speaker': p.get('speaker'),
                'score': p.get('score', 0.0),
                'youtube_url': p['youtube_url']
            }
            citations.append(citation)
        
        return citations
    
    def _extract_sources_from_compressed(
        self,
        compressed_parents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract unique source episodes."""
        seen_videos = set()
        sources = []
        
        for p in compressed_parents:
            if p['video_id'] and p['video_id'] not in seen_videos:
                seen_videos.add(p['video_id'])
                sources.append({
                    'video_id': p['video_id'],
                    'youtube_url': p['youtube_url']
                })
        
        return sources
    
    def _create_youtube_url(self, video_id: str, start_seconds: float) -> str:
        """Create YouTube deep link."""
        adjusted_start = max(0, int(start_seconds) - 5)  # 5 second lead-in
        return f"https://www.youtube.com/watch?v={video_id}&t={adjusted_start}s"
