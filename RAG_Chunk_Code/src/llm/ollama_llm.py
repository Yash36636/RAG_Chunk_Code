"""
Ollama LLM Client - Local inference (no API keys)
Fallback option when cloud providers unavailable
"""

import os
import json
import requests
from typing import Iterator, Optional

from .base import BaseLLM


class OllamaLLM(BaseLLM):
    """
    Local LLM client using Ollama.
    Best for: offline use, privacy, no API costs
    
    Recommended models for CPU:
    - qwen2.5:3b-instruct (fast, good quality)
    - phi3:mini (very fast)
    - mistral (quality, but slower on CPU)
    """
    
    def __init__(
        self,
        model: str = "qwen2.5:3b-instruct",
        base_url: str = "http://localhost:11434",
        max_tokens: int = 600,
        temperature: float = 0.15
    ):
        """
        Initialize Ollama client.
        
        Args:
            model: Ollama model name
            base_url: Ollama server URL
            max_tokens: Maximum output tokens
            temperature: Response temperature
        """
        # Allow model override from environment
        self.model = os.getenv("OLLAMA_MODEL", model)
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Verify Ollama is running
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                print(f"   [OK] Ollama connected: {base_url}")
                print(f"   [OK] Using model: {self.model}")
            else:
                print(f"   [WARNING] Ollama returned status {response.status_code}")
        except Exception as e:
            print(f"   [WARNING] Could not connect to Ollama: {e}")
            print(f"   Make sure Ollama is running: ollama serve")
    
    def generate(self, prompt: str) -> str:
        """
        Generate text using local LLM (non-streaming).
        
        Args:
            prompt: Complete prompt including system instructions
            
        Returns:
            Generated text
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": self.max_tokens,
                        "temperature": self.temperature,
                        "top_p": 0.95,
                        "top_k": 40,
                        "num_ctx": 4096
                    }
                },
                timeout=180
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result["response"].strip()
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Could not connect to Ollama. Make sure it's running:\n"
                "  1. Install: https://ollama.com\n"
                "  2. Pull model: ollama pull qwen2.5:3b-instruct\n"
                "  3. Start server: ollama serve"
            )
        except Exception as e:
            raise Exception(f"Ollama generation failed: {e}")
    
    def generate_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generate text with explicit system and user prompts.
        
        Args:
            system_prompt: System instructions
            user_prompt: User's message/question
            
        Returns:
            Generated text
        """
        # Ollama uses /api/chat for system/user messages
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": self.max_tokens,
                        "temperature": self.temperature,
                        "top_p": 0.95,
                        "top_k": 40,
                        "num_ctx": 4096
                    }
                },
                timeout=180
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result["message"]["content"].strip()
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Could not connect to Ollama. Make sure it's running."
            )
        except Exception as e:
            raise Exception(f"Ollama generation failed: {e}")
    
    def generate_stream(self, prompt: str) -> Iterator[str]:
        """
        Generate text with streaming.
        
        Args:
            prompt: Complete prompt
            
        Yields:
            Text tokens as generated
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "num_predict": self.max_tokens,
                        "temperature": self.temperature,
                        "top_p": 0.95,
                        "top_k": 40,
                        "num_ctx": 4096
                    }
                },
                stream=True,
                timeout=180
            )
            
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
            
        except Exception as e:
            raise Exception(f"Ollama streaming failed: {e}")
    
    def get_provider_name(self) -> str:
        return f"ollama/{self.model}"
