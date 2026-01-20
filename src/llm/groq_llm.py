"""
Groq LLM Client - Ultra-fast cloud inference with prompt caching
Recommended for production use

PROMPT CACHING:
- System prompt is STATIC and identical across requests
- Groq optimizes for repeated prefixes
- User prompt changes, system prompt stays constant
"""

import os
from typing import Iterator, Optional, List, Dict

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None

from .base import BaseLLM

# Import cached prompts (STATIC - never changes per request)
try:
    from src.prompts.cached_system import (
        CACHED_SYSTEM_PROMPT,
        CONVERSATIONAL_PM_PROMPT,
        MEMORY_SUMMARIZATION_PROMPT,
        FOLLOWUP_GENERATION_PROMPT
    )
except ImportError:
    # Fallback if prompts not found
    CACHED_SYSTEM_PROMPT = "You are a helpful assistant."
    CONVERSATIONAL_PM_PROMPT = CACHED_SYSTEM_PROMPT
    MEMORY_SUMMARIZATION_PROMPT = "Summarize this conversation."
    FOLLOWUP_GENERATION_PROMPT = "Generate follow-up questions."


class GroqLLM(BaseLLM):
    """
    Groq LLM client for ultra-fast inference with prompt caching.
    
    Features:
    - Static system prompt (enables Groq prompt caching)
    - Structured message assembly
    - Support for conversation context
    
    Recommended models:
    - llama-3.1-8b-instant (fast, good quality)
    - llama-3.1-70b-versatile (higher quality, slightly slower)
    - mixtral-8x7b-32768 (good for complex tasks)
    """
    
    def __init__(
        self,
        model: str = "llama-3.1-8b-instant",
        max_tokens: int = 600,
        temperature: float = 0.2,
        api_key: Optional[str] = None
    ):
        """
        Initialize Groq client.
        
        Args:
            model: Groq model to use
            max_tokens: Maximum output tokens
            temperature: Response temperature (lower = more deterministic)
            api_key: Groq API key (or use GROQ_API_KEY env var)
        """
        if not GROQ_AVAILABLE:
            raise ImportError(
                "Groq package not installed. Run: pip install groq"
            )
        
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY not set. Get one at: https://console.groq.com"
            )
        
        self.client = Groq(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        print(f"   [OK] Groq client ready (model: {model})")
    
    def generate(self, prompt: str) -> str:
        """
        Generate text using Groq with default system prompt.
        
        Args:
            prompt: Complete prompt with context
            
        Returns:
            Generated text
        """
        return self.generate_with_system(self.DEFAULT_SYSTEM_PROMPT, prompt)
    
    def generate_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generate text with explicit system and user prompts.
        
        Args:
            system_prompt: System instructions
            user_prompt: User's message/question
            
        Returns:
            Generated text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=0.95,
                stream=False
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"Groq generation failed: {e}")
    
    def generate_stream(self, prompt: str) -> Iterator[str]:
        """
        Generate text with streaming (tokens appear as generated).
        
        Args:
            prompt: Complete prompt with context
            
        Yields:
            Text tokens as they are generated
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": CACHED_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=0.95,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise Exception(f"Groq streaming failed: {e}")
    
    def generate_with_structured_context(
        self,
        summary_memory: str,
        rag_context: str,
        recent_turns: str,
        user_query: str
    ) -> str:
        """
        Generate with proper prompt assembly order for caching.
        
        Assembly Order (CRITICAL for prompt caching):
        [CACHED SYSTEM PROMPT] ← static, cached by Groq
        -----------------------------------------
        [SUMMARY MEMORY]       ← small, dynamic
        -----------------------------------------
        [RAG CONTEXT]          ← FAISS results
        -----------------------------------------
        [RECENT TURNS]         ← last 2 turns
        -----------------------------------------
        [USER QUERY]
        
        Args:
            summary_memory: Compressed conversation summary
            rag_context: Retrieved chunks with scores
            recent_turns: Last 2 conversation turns
            user_query: Current user question
            
        Returns:
            Generated answer
        """
        # Build user prompt with proper sections
        user_prompt_parts = []
        
        if summary_memory:
            user_prompt_parts.append(f"PREVIOUS CONTEXT:\n{summary_memory}")
        
        if rag_context:
            user_prompt_parts.append(f"RETRIEVED SOURCES:\n{rag_context}")
        
        if recent_turns:
            user_prompt_parts.append(f"RECENT CONVERSATION:\n{recent_turns}")
        
        user_prompt_parts.append(f"USER QUESTION:\n{user_query}")
        
        user_prompt = "\n\n---\n\n".join(user_prompt_parts)
        
        return self.generate_with_system(CACHED_SYSTEM_PROMPT, user_prompt)
    
    def generate_conversational(self, query: str, conversation_context: str = "") -> str:
        """
        Generate conversational response (low confidence fallback).
        Uses the conversational PM prompt.
        
        Args:
            query: User's question
            conversation_context: Previous conversation context
            
        Returns:
            Friendly, mentor-like response
        """
        user_prompt = query
        if conversation_context:
            user_prompt = f"Context:\n{conversation_context}\n\nUser: {query}"
        
        return self.generate_with_system(CONVERSATIONAL_PM_PROMPT, user_prompt)
    
    def summarize_conversation(self, previous_summary: str, recent_turns: str) -> str:
        """
        Summarize conversation for memory compression.
        
        Args:
            previous_summary: Existing summary (if any)
            recent_turns: Recent turns to incorporate
            
        Returns:
            Compressed PM-focused summary
        """
        prompt_parts = []
        
        if previous_summary:
            prompt_parts.append(f"Previous Summary:\n{previous_summary}")
        
        prompt_parts.append(f"Recent Conversation:\n{recent_turns}")
        prompt_parts.append("Create an updated summary that incorporates both.")
        
        user_prompt = "\n\n".join(prompt_parts)
        
        try:
            # Use lower max_tokens for summarization
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": MEMORY_SUMMARIZATION_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=150,
                top_p=0.9,
                stream=False
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"   [WARN] Summarization failed: {e}")
            return previous_summary  # Keep old summary on failure
    
    def generate_followups(self, answer_text: str, source_topics: str) -> List[str]:
        """
        Generate follow-up questions based on answer and sources.
        
        Args:
            answer_text: The answer just given
            source_topics: Key topics from sources
            
        Returns:
            List of 3 follow-up questions
        """
        user_prompt = f"""Answer given:
{answer_text}

Source topics:
{source_topics}

Generate 3 follow-up questions:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": FOLLOWUP_GENERATION_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=100,
                top_p=0.9,
                stream=False
            )
            
            raw = response.choices[0].message.content.strip()
            # Parse questions (one per line)
            questions = [q.strip() for q in raw.split('\n') if q.strip()]
            # Clean any numbering or bullets
            questions = [q.lstrip('0123456789.-•) ') for q in questions]
            return questions[:3]  # Max 3
            
        except Exception as e:
            print(f"   [WARN] Follow-up generation failed: {e}")
            return []
    
    def get_provider_name(self) -> str:
        return f"groq/{self.model}"
