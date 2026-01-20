"""
Base LLM Interface
All LLM providers must implement this interface
"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional


class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.
    Ensures consistent interface across Groq, Ollama, Gemini, etc.
    """
    
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate text from prompt (non-streaming).
        
        Args:
            prompt: Complete prompt including context
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def generate_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generate text with explicit system and user prompts.
        
        Args:
            system_prompt: System instructions
            user_prompt: User's message/question
            
        Returns:
            Generated text response
        """
        pass
    
    def generate_stream(self, prompt: str) -> Iterator[str]:
        """
        Generate text with streaming (optional).
        Default implementation falls back to non-streaming.
        
        Args:
            prompt: Complete prompt including context
            
        Yields:
            Text tokens as they are generated
        """
        # Default: non-streaming fallback
        yield self.generate(prompt)
    
    def get_provider_name(self) -> str:
        """Return the provider name for logging."""
        return self.__class__.__name__
