# Files Included in RAG_Chunk_Code

This document lists all files included in this folder.

## Core Source Modules (`src/` directory)

1. **`src/__init__.py`** - Package initialization, exports all public APIs
2. **`src/ingestion.py`** - File ingestion, YAML frontmatter parsing, metadata extraction
3. **`src/parser.py`** - Transcript parsing into segments (single source of truth for segments)
4. **`src/cleaning.py`** - Text cleaning, artifact removal, sentence reconstruction
5. **`src/chunking.py`** - Hierarchical parent-child chunking with segment index tracking
6. **`src/embedding.py`** - Embedding generation (OpenAI API integration)
7. **`src/pipeline.py`** - Main pipeline orchestrator, enrichment (happens once)
8. **`src/storage.py`** - JSON storage for chunks (no ID rewriting, no enrichment recomputation)
9. **`src/github_integration.py`** - GitHub repository cloning, topic index parsing

## Main Scripts

10. **`run_lennys_pipeline.py`** - Main entry point to process product management episodes
11. **`process_topic_episodes.py`** - Core function to process episodes from GitHub topic files
12. **`test_fixes.py`** - Comprehensive test suite verifying all 6 fixes

## Documentation

13. **`README.md`** - Complete documentation with usage instructions
14. **`requirements.txt`** - Python package dependencies
15. **`FILES_INCLUDED.md`** - This file

## Total Files: 15

## Key Features Implemented

✅ **FIX 1**: Segments created ONLY by TranscriptParser  
✅ **FIX 2**: Parent chunks track segment indices  
✅ **FIX 3**: Child chunks use parent segments only (index-based)  
✅ **FIX 4**: Enrichment happens once (pipeline only)  
✅ **FIX 5**: ID assignment single source of truth  
✅ **FIX 6**: Safety checks prevent cross-parent contamination  

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python test_fixes.py

# Process episodes
python run_lennys_pipeline.py
```

## Output

Chunks are saved to `chunks_product_management/` directory with:
- Sequential IDs: `parent_0`, `parent_1`, `child_0`, `child_1`, etc.
- Correct `enriched_text` alignment
- Complete metadata
- YouTube deep links
