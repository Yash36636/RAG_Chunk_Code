# Free Embedding Guide

Complete guide for using **free, local embedding** with Sentence Transformers + FAISS.

## 🎯 Quick Start

### 1. Install Dependencies

```bash
pip install sentence-transformers faiss-cpu torch
```

**For GPU support** (optional, faster):
```bash
pip install sentence-transformers faiss-gpu torch
```

### 2. Embed Chunks (Free)

```bash
python embed_chunks_free.py --chunks-dir chunks_product_management
```

That's it! No API keys needed. Runs completely locally.

### 3. Query

```bash
python retrieve_chunks_free.py --query "How to prioritize features?"
```

## 📊 Model Options

### Recommended: `all-MiniLM-L6-v2` (Default)

**Best for:**
- Fast embedding (30-60 min for 8,500 chunks)
- Low memory usage (works on CPU)
- Good baseline quality
- Production-ready

**Specs:**
- Dimensions: 384
- Speed: Very fast
- Memory: Low (~100MB)
- Quality: Good

### Better Quality: `all-mpnet-base-v2`

**Best for:**
- Higher retrieval quality
- Better semantic understanding
- When you have more CPU/memory

**Specs:**
- Dimensions: 768
- Speed: Slower
- Memory: Medium (~400MB)
- Quality: Better

### Best Quality: `intfloat/e5-large-v2`

**Best for:**
- Highest quality retrieval
- When you have GPU available
- Quality-critical applications

**Specs:**
- Dimensions: 1024
- Speed: Slow (needs GPU)
- Memory: High (~2GB)
- Quality: Best (open-source)

### Good Balance: `intfloat/e5-small-v2`

**Best for:**
- Better quality than MiniLM
- Still fast and lightweight
- Good middle ground

**Specs:**
- Dimensions: 384
- Speed: Fast
- Memory: Low (~200MB)
- Quality: Better than MiniLM

## 🚀 Usage Examples

### Basic Embedding

```bash
# Use default model (MiniLM)
python embed_chunks_free.py --chunks-dir chunks_product_management
```

### Use Better Model

```bash
# Use mpnet for better quality
python embed_chunks_free.py \
  --chunks-dir chunks_product_management \
  --model sentence-transformers/all-mpnet-base-v2
```

### Use GPU (if available)

```bash
# Automatically uses GPU if available
python embed_chunks_free.py \
  --chunks-dir chunks_product_management \
  --device cuda
```

### Custom Index Paths

```bash
python embed_chunks_free.py \
  --chunks-dir chunks_product_management \
  --core-index ./my_indexes/core \
  --longtail-index ./my_indexes/longtail
```

### Query with Longtail

```bash
python retrieve_chunks_free.py \
  --query "Did anyone mention working with designers?" \
  --use-longtail
```

## 📈 Performance Comparison

| Model | Embedding Time (8.5k chunks) | Query Latency | Quality | Memory |
|-------|------------------------------|---------------|---------|--------|
| all-MiniLM-L6-v2 | 30-45 min (CPU) | <50ms | Good | Low |
| all-mpnet-base-v2 | 60-90 min (CPU) | <100ms | Better | Medium |
| e5-large-v2 | 20-30 min (GPU) | <100ms | Best | High |
| e5-small-v2 | 40-60 min (CPU) | <60ms | Better | Low |

## 🔍 How It Works

1. **Chunk Classification**: Filters out sponsors/banter (reduces ~12,790 → ~8,500 chunks)
2. **Two-Tier Indexing**: Separates core (content) and longtail (anecdotes)
3. **Local Embedding**: Uses Sentence Transformers (no API calls)
4. **FAISS Storage**: Stores vectors locally (fast, free)
5. **Retrieval**: Fast similarity search with parent expansion

## 💾 Storage

FAISS indexes are saved locally:
- `./faiss_indexes/product-management-core.index`
- `./faiss_indexes/product-management-longtail.index`
- `./faiss_indexes/product-management-core.meta` (metadata)
- `./faiss_indexes/product-management-longtail.meta` (metadata)

**Total size**: ~50-200MB depending on model (much smaller than Pinecone)

## 🔄 Re-embedding

To re-embed with a different model:

1. Delete old indexes (or use different paths):
```bash
rm -rf ./faiss_indexes/
```

2. Run embedding again with new model:
```bash
python embed_chunks_free.py --model intfloat/e5-large-v2
```

## 🧪 Testing Models

To compare models on a sample:

```python
from src.free_embedding import FreeEmbeddingGenerator
import time

models = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/all-mpnet-base-v2",
    "intfloat/e5-small-v2"
]

test_texts = ["How to prioritize features?", "What is product management?"]

for model_name in models:
    print(f"\nTesting {model_name}...")
    gen = FreeEmbeddingGenerator(model_name)
    
    start = time.time()
    embeddings = gen.embed_batch(test_texts)
    elapsed = time.time() - start
    
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Dimensions: {gen.dimensions}")
```

## ⚙️ Advanced Options

### Batch Size

Larger batches = faster embedding, more memory:

```bash
python embed_chunks_free.py \
  --chunks-dir chunks_product_management \
  --batch-size 128
```

### CPU-Only Mode

Force CPU even if GPU available:

```bash
python embed_chunks_free.py \
  --chunks-dir chunks_product_management \
  --device cpu
```

## 🆚 Free vs Paid Comparison

| Feature | Free (This) | Paid (OpenAI + Pinecone) |
|---------|-------------|--------------------------|
| Cost | $0 | ~$0.33 embedding + monthly |
| Speed | Fast (local) | Fast (cloud) |
| Quality | Good-Best | Excellent |
| Privacy | 100% local | Cloud-based |
| Scalability | Limited by RAM | Unlimited |
| Setup | Easy | Requires API keys |

## ✅ Advantages of Free Version

1. **No API costs** - Completely free
2. **Privacy** - All data stays local
3. **No rate limits** - Process as fast as your hardware allows
4. **Offline** - Works without internet
5. **Customizable** - Can fine-tune models if needed

## 🎯 Recommendation

**Start with**: `all-MiniLM-L6-v2` (default)
- Fast, good quality, works everywhere

**Upgrade to**: `all-mpnet-base-v2` if you need better quality
- Still runs on CPU, better semantic understanding

**Best quality**: `intfloat/e5-large-v2` if you have GPU
- Top open-source quality, needs GPU for speed

## 📝 Next Steps

1. **Embed chunks**: `python embed_chunks_free.py`
2. **Test retrieval**: `python retrieve_chunks_free.py --query "your question"`
3. **Compare models**: Try different models and compare results
4. **Build interface**: Integrate with your chatbot/application

## 🐛 Troubleshooting

**"CUDA out of memory"**
- Use CPU: `--device cpu`
- Reduce batch size: `--batch-size 32`
- Use smaller model: `all-MiniLM-L6-v2`

**"Model not found"**
- Models download automatically on first use
- Check internet connection
- Try: `pip install --upgrade sentence-transformers`

**"FAISS index not found"**
- Run embedding first: `python embed_chunks_free.py`
- Check index paths match

**Slow embedding**
- Use GPU if available: `--device cuda`
- Increase batch size: `--batch-size 128`
- Use smaller model: `all-MiniLM-L6-v2`
