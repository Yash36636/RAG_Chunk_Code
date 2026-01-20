"""
Prompt loader utilities
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(filename: str) -> str:
    """
    Load a prompt template from file.
    
    Args:
        filename: Name of the prompt file (e.g., "rag_pm.txt")
        
    Returns:
        Prompt text content
    """
    prompt_path = PROMPTS_DIR / filename
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {filename}")
    
    return prompt_path.read_text(encoding="utf-8")
