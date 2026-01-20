"""
Free Embedding Generator using Sentence Transformers
No API keys required - runs locally
"""

from typing import List, Optional
import numpy as np

class FreeEmbeddingGenerator:
    """Free embedding generator using Sentence Transformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", device: Optional[str] = None):
        """
        Initialize with Sentence Transformers.
        
        Args:
            model_name: Sentence Transformers model name
                - "sentence-transformers/all-MiniLM-L6-v2" (384 dims, fast) - RECOMMENDED BASELINE
                - "sentence-transformers/all-mpnet-base-v2" (768 dims, better quality)
                - "intfloat/e5-large-v2" (1024 dims, best quality, needs GPU)
                - "intfloat/e5-small-v2" (384 dims, good quality)
            device: "cuda" for GPU, "cpu" for CPU (auto-detects if None)
        """
        import os
        # Prevent TensorFlow from being imported (we don't need it for sentence-transformers)
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        os.environ['TRANSFORMERS_NO_TF'] = '1'
        
        try:
            # Suppress TensorFlow warnings/errors during import
            import warnings
            warnings.filterwarnings('ignore', category=UserWarning)
            
            from sentence_transformers import SentenceTransformer
            
            # Auto-detect device if not specified
            if device is None:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            print(f"Loading model: {model_name} on {device}...")
            self.model = SentenceTransformer(model_name, device=device)
            self.dimensions = self.model.get_sentence_embedding_dimension()
            self.model_name = model_name
            self.device = device
            
            print(f"Model loaded: {model_name} ({self.dimensions} dimensions) on {device}")
            
        except ImportError as e:
            raise ImportError(
                f"sentence-transformers required. Install with: pip install sentence-transformers\n"
                f"Original error: {e}"
            )
        except Exception as e:
            # Handle TensorFlow DLL errors gracefully
            if "tensorflow" in str(e).lower() or "dll" in str(e).lower():
                raise ImportError(
                    f"TensorFlow import error detected. This is not needed for sentence-transformers.\n"
                    f"Try: pip uninstall tensorflow tensorflow-intel -y\n"
                    f"Or create a clean environment. Original error: {e}"
                )
            raise
    
    def embed(self, text: str, normalize: bool = True) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            normalize: Whether to normalize embeddings (recommended for cosine similarity)
            
        Returns:
            Embedding vector
        """
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=False
        )
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str], normalize: bool = True, batch_size: int = 64, 
                   show_progress: bool = True) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batched for efficiency).
        
        Args:
            texts: List of texts to embed
            normalize: Whether to normalize embeddings (recommended for cosine similarity)
            batch_size: Batch size for processing
            show_progress: Whether to show progress bar
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            batch_size=batch_size,
            show_progress_bar=show_progress
        )
        return embeddings.tolist()
