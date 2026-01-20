# Embedding Strategy Guide

This guide explains the two-tier embedding system implemented for the video RAG pipeline.

## Overview

The embedding system is designed for **12,790 child chunks** from **142 episodes**. Instead of embedding everything naively, we use:

1. **Chunk Classification** - Filter out non-semantic content before embedding
2. **Two-Tier Indexing** - Separate core knowledge from longtail stories
3. **Parent Expansion** - Include context during retrieval, not embedding
4. **Smart Retrieval** - Deduplication and grouping for coherent answers

## Architecture

### Step 1: Chunk Classification

Before embedding, chunks are classified into:

- **`content`** - Advice, frameworks, opinions → **Core Index**
- **`anecdote`** - Personal stories → **Longtail Index**
- **`meta`** - Podcast transitions → **Skip**
- **`sponsor`** - Ads, promos → **Skip**
- **`banter`** - Jokes, filler → **Skip**

**Expected reduction**: ~12,790 → ~8,000-9,000 embeddable chunks

### Step 2: Two-Tier Embedding

**Core Index** (`product-management-core`):
- Contains `content` chunks (~6,000-7,000)
- Used for: advice, how-to questions, conceptual queries
- Default search target

**Longtail Index** (`product-management-longtail`):
- Contains `anecdote` chunks (~2,000-3,000)
- Used for: "did X ever say...", story-based questions
- Searched only if core results are weak

### Step 3: Embedding Input Format

**What gets embedded:**
```
Video: {title}
Guest: {guest}
Topics: {topics}
Text: {child.text}
```

**What is excluded:**
- ❌ Timestamps
- ❌ YouTube URLs
- ❌ Parent text (too long, causes topic bleeding)
- ❌ Episode descriptions

### Step 4: Retrieval Strategy

**Default retrieval:**
- Search: Core index only
- Top-K: 12 results
- Minimum score: 0.7

**Conditional expansion:**
- If < 5 strong hits OR low scores:
  - Also search: Longtail index
  - Top-K: 6 additional results

### Step 5: Parent Expansion

For each retrieved child chunk:
- Fetch its parent chunk
- Include ±25% surrounding text
- **Never embed parent** (only used for context)

This provides:
- Narrative continuity
- Less hallucination
- Stronger synthesis

### Step 6: Deduplication & Grouping

**Rules:**
- Keep top 1-2 chunks per parent
- Keep top 3 chunks per episode
- Remove exact duplicates

**Prevents:**
- Repetitive answers
- Bloated prompts

## Usage

### 1. Embed Chunks

```bash
python embed_chunks.py \
  --chunks-dir chunks_product_management \
  --openai-key YOUR_OPENAI_KEY \
  --pinecone-key YOUR_PINECONE_KEY \
  --pinecone-env YOUR_PINECONE_ENV \
  --core-index product-management-core \
  --longtail-index product-management-longtail
```

Or set environment variables:
```bash
export OPENAI_API_KEY="your-key"
export PINECONE_API_KEY="your-key"
export PINECONE_ENVIRONMENT="your-env"

python embed_chunks.py --chunks-dir chunks_product_management
```

### 2. Query Indexes

```bash
python retrieve_chunks.py \
  --query "How to prioritize features?" \
  --openai-key YOUR_OPENAI_KEY \
  --pinecone-key YOUR_PINECONE_KEY \
  --pinecone-env YOUR_PINECONE_ENV
```

**With longtail search:**
```bash
python retrieve_chunks.py \
  --query "Did anyone mention working with designers?" \
  --use-longtail \
  --openai-key YOUR_OPENAI_KEY \
  --pinecone-key YOUR_PINECONE_KEY \
  --pinecone-env YOUR_PINECONE_ENV
```

## Python API

### Embedding

```python
from src import (
    EmbeddingGenerator,
    PineconeStore,
    TwoTierEmbeddingPipeline
)

# Initialize
embedding_gen = EmbeddingGenerator(
    model_name="text-embedding-3-large",
    dimensions=1536,
    api_key=openai_key
)

core_store = PineconeStore(
    api_key=pinecone_key,
    environment=pinecone_env,
    index_name="product-management-core"
)

longtail_store = PineconeStore(
    api_key=pinecone_key,
    environment=pinecone_env,
    index_name="product-management-longtail"
)

pipeline = TwoTierEmbeddingPipeline(
    embedding_generator=embedding_gen,
    core_store=core_store,
    longtail_store=longtail_store
)

# Index chunks
stats = pipeline.index_chunks(
    child_chunks=child_chunks,
    parent_chunks=parent_chunks,
    metadata=metadata,
    enriched_texts=enriched_texts
)
```

### Retrieval

```python
from src import RetrievalPipeline

# Initialize (requires TwoTierEmbeddingPipeline instance)
retrieval = RetrievalPipeline(
    embedding_generator=embedding_gen,
    core_store=core_store,
    longtail_store=longtail_store,
    two_tier_pipeline=pipeline
)

# Query
results = retrieval.retrieve(
    query="How to prioritize features?",
    use_longtail=False
)

# Results include parent expansion
for result in results:
    print(f"Score: {result.score}")
    print(f"Text: {result.text}")
    print(f"Parent Context: {result.parent_text}")
    print(f"Deep Link: {retrieval.create_deep_link(result.video_id, result.start_seconds)}")
```

## Cost Estimate

Assuming:
- ~8,500 embedded chunks
- ~300 tokens per chunk
- ~2.5M tokens total

**Embedding cost** (OpenAI `text-embedding-3-large`):
- ~$0.13 per 1M tokens
- **Total: ~$0.33** (one-time)

**Query cost**:
- ~$0.0001 per query (very cheap)

## Performance

- **Embedding time**: ~30-60 minutes for 8,500 chunks
- **Query latency**: < 500ms (Pinecone)
- **Recall**: High (two-tier ensures coverage)
- **Precision**: High (classification + deduplication)

## Key Benefits

1. **Reduced noise** - Sponsor/banter filtered out
2. **Better precision** - Core index for most queries
3. **Controlled cost** - Only embed what matters
4. **Coherent answers** - Parent expansion + deduplication
5. **Scalable** - Works for 500+ episodes

## Next Steps

After embedding, you can:
1. Build a query interface (web app, CLI, API)
2. Integrate with LLM for answer synthesis
3. Add hybrid search (keyword + semantic)
4. Monitor retrieval quality and adjust thresholds

## Troubleshooting

**"No results found"**
- Check minimum score threshold (default: 0.7)
- Try `--use-longtail` flag
- Verify indexes exist in Pinecone

**"Low quality results"**
- Adjust `min_score_threshold` in RetrievalPipeline
- Review chunk classification rules
- Check embedding input format

**"Parent expansion missing"**
- Ensure parent chunks were indexed
- Check `parent_id` mapping in chunks
