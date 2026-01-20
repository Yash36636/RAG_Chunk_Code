"""
LLM Router - Intelligent provider selection
Supports: groq (default), ollama (fallback), auto (smart selection)
"""

import os
from typing import Optional

from .base import BaseLLM
from .groq_llm import GroqLLM, GROQ_AVAILABLE
from .ollama_llm import OllamaLLM


class LLMRouter:
    """
    Intelligent LLM provider router.
    
    Supports:
    - groq: Ultra-fast cloud inference (default)
    - ollama: Local inference (fallback)
    - auto: Try groq first, fallback to ollama
    """
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize router with specified provider.
        
        Args:
            provider: "groq", "ollama", or "auto" (from env if not specified)
        """
        self.provider = provider or os.getenv("LLM_PROVIDER", "auto").lower()
        self.llm: Optional[BaseLLM] = None
        self.actual_provider: Optional[str] = None
    
    def get_llm(self) -> BaseLLM:
        """
        Get the appropriate LLM based on configuration.
        
        Returns:
            Configured LLM instance
        """
        if self.llm is not None:
            return self.llm
        
        if self.provider == "groq":
            self.llm = self._init_groq()
            
        elif self.provider == "ollama":
            self.llm = self._init_ollama()
            
        elif self.provider == "auto":
            self.llm = self._init_auto()
            
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {self.provider}")
        
        return self.llm
    
    def _init_groq(self) -> BaseLLM:
        """Initialize Groq (will raise if API key missing)."""
        try:
            llm = GroqLLM()
            self.actual_provider = "groq"
            return llm
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Groq: {e}")
    
    def _init_ollama(self) -> BaseLLM:
        """Initialize Ollama."""
        try:
            llm = OllamaLLM()
            self.actual_provider = "ollama"
            return llm
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Ollama: {e}")
    
    def _init_auto(self) -> BaseLLM:
        """Auto-select: try Groq first, fallback to Ollama."""
        # Try Groq first (fast, reliable)
        if GROQ_AVAILABLE and os.getenv("GROQ_API_KEY"):
            try:
                print("   [INFO] Trying Groq (fast cloud inference)...")
                llm = GroqLLM()
                self.actual_provider = "groq"
                print("   [OK] Using Groq")
                return llm
            except Exception as e:
                print(f"   [INFO] Groq not available: {e}")
        
        # Fallback to Ollama
        try:
            print("   [INFO] Falling back to Ollama (local)...")
            llm = OllamaLLM()
            self.actual_provider = "ollama"
            print("   [OK] Using Ollama")
            return llm
        except Exception as e:
            print(f"   [ERROR] Ollama also failed: {e}")
        
        raise RuntimeError(
            "No LLM provider available!\n"
            "Options:\n"
            "  1. Set GROQ_API_KEY for fast cloud inference\n"
            "  2. Start Ollama: ollama serve"
        )


def get_llm(provider: Optional[str] = None) -> BaseLLM:
    """
    Convenience function to get configured LLM.
    
    Args:
        provider: Override provider selection ("groq", "ollama", "auto")
        
    Returns:
        Configured LLM instance
    """
    router = LLMRouter(provider)
    return router.get_llm()
