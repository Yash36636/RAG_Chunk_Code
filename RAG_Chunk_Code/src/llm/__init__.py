"""
LLM Provider Abstraction Layer
Supports: Groq (fast), Ollama (local), Gemini (cloud)
"""

from .base import BaseLLM
from .groq_llm import GroqLLM
from .ollama_llm import OllamaLLM
from .router import get_llm, LLMRouter

__all__ = [
    'BaseLLM',
    'GroqLLM',
    'OllamaLLM',
    'get_llm',
    'LLMRouter'
]
