"""
Product Wisdom Hub API
Production-grade RAG with confidence gating, safety guards, and conversation memory
"""

import os
import sys
import time
import hashlib
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Set environment variables
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src import (
    RetrievalPipeline,
    TwoTierEmbeddingPipeline,
    FreeEmbeddingGenerator,
    FAISSStore,
    ParentChunkLoader,
    UnifiedSynthesizer,
    get_llm
)
from src.query_router import is_pm_intent, should_use_rag
from src.safety import get_safety_response
from src.conversational import conversational_pm_answer
from src.confidence import (
    compute_confidence, 
    apply_diversity_constraint, 
    filter_by_score,
    get_confidence_prompt_modifier,
    limit_sources_by_answer_length
)
from src.memory import session_store
from src.followup_generator import (
    generate_followups, 
    extract_source_topics, 
    summarize_memory
)

# ================================================
# FASTAPI APP
# ================================================
app = FastAPI(
    title="Product Wisdom Hub API",
    description="Production-grade RAG with confidence gating and conversation memory",
    version="3.2.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================
# GLOBAL OBJECTS (LOADED ONCE AT STARTUP)
# ================================================
print(">> Starting Product Wisdom Hub server...")
print("=" * 70)

# Model configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSION = 384
DEVICE = "cpu"

# Initialize embedding generator
print(f">> Loading embedding model: {MODEL_NAME}...")
start = time.time()
embedding_generator = FreeEmbeddingGenerator(
    model_name=MODEL_NAME,
    device=DEVICE
)
print(f"   [OK] Model loaded in {time.time() - start:.2f}s")

# Initialize vector stores
print(">> Loading FAISS indexes...")
start = time.time()
core_store = FAISSStore(
    index_path="./faiss_indexes/product-management-core",
    dimension=DIMENSION
)
print(f"   [OK] Core index loaded: {core_store.index.ntotal} vectors")

longtail_store = FAISSStore(
    index_path="./faiss_indexes/product-management-longtail",
    dimension=DIMENSION
)
print(f"   [OK] Longtail index loaded in {time.time() - start:.2f}s")

# Initialize two-tier pipeline
two_tier_pipeline = TwoTierEmbeddingPipeline(
    embedding_generator=embedding_generator,
    core_store=core_store,
    longtail_store=longtail_store
)

# Initialize retrieval pipeline
retrieval_pipeline = RetrievalPipeline(
    embedding_generator=embedding_generator,
    core_store=core_store,
    longtail_store=longtail_store,
    two_tier_pipeline=two_tier_pipeline,
    core_top_k=20,
    longtail_top_k=10,
    min_score_threshold=0.3,
    parent_expansion_percent=0.25
)

# Load parent chunks (ONCE, into memory)
print(">> Loading parent chunks into memory...")
start = time.time()
parent_loader = ParentChunkLoader(chunks_dir="chunks_product_management")
stats = parent_loader.get_stats()
print(f"   [OK] Loaded {stats['total_parents']} parent chunks")
print(f"   [OK] Parent chunks loaded in {time.time() - start:.2f}s")

# Initialize LLM and synthesizer
print(">> Initializing LLM provider...")
llm_provider = os.getenv("LLM_PROVIDER", "auto")
print(f"   [INFO] LLM_PROVIDER: {llm_provider}")

answer_synthesizer = None
llm_client = None
actual_provider = None

try:
    llm_client = get_llm(llm_provider)
    answer_synthesizer = UnifiedSynthesizer(
        llm_client=llm_client,
        mode="fast"
    )
    actual_provider = llm_client.get_provider_name()
    print(f"   [OK] Answer synthesizer ready (provider: {actual_provider})")
except Exception as e:
    print(f"   [ERROR] Failed to initialize LLM: {e}")
    print("   [WARNING] Running in retrieval-only mode")

print("=" * 70)
print("[OK] Product Wisdom Hub ready! (with conversation memory)")
print("=" * 70)

# ================================================
# QUERY CACHE
# ================================================
query_cache = {}
cache_hits = 0
cache_misses = 0

# ================================================
# REQUEST/RESPONSE MODELS (STRICT CONTRACT)
# ================================================

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None  # For conversation memory
    use_longtail: bool = False
    mode: str = "fast"

class AnswerContent(BaseModel):
    """Structured answer content"""
    direct_answer: str
    key_ideas: List[str]
    common_pitfall: str
    summary: str

class SourceItem(BaseModel):
    """Citation source with full metadata"""
    video_title: str
    speaker: str
    thumbnail: str
    timestamp: str
    link: str
    score: float
    text_preview: str

class QueryResponse(BaseModel):
    """
    STRICT RESPONSE CONTRACT
    Frontend must render ONLY what is returned here
    """
    answer: AnswerContent
    sources: List[SourceItem]
    confidence: str  # "low" | "medium" | "high"
    mode: str  # "rag" | "conversation" | "safety"
    latency_ms: int
    query: str
    session_id: str  # Return session ID for frontend to track
    turn_count: int = 0  # Number of turns in this session
    followups: List[str] = []  # Smart follow-up questions
    safety_refusal: bool = False  # True if query was refused for safety

# ================================================
# HELPER FUNCTIONS
# ================================================

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

def get_thumbnail_url(video_id: str) -> str:
    """Get YouTube thumbnail URL"""
    return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"

def normalize_output(text: str) -> str:
    """
    Defensive normalizer to strip markdown leaks before frontend.
    
    Fixes common LLM format violations:
    - ### headers → plain text
    - **bold** → plain text
    - - bullets → • bullets
    - Numbered lists → bullet points
    """
    import re
    
    # Remove markdown headers (###, ##, #)
    text = re.sub(r'^#{1,3}\s*', '', text, flags=re.MULTILINE)
    
    # Remove bold markers
    text = text.replace('**', '')
    
    # Convert dashes to bullets at start of lines
    text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\s+', '• ', text, flags=re.MULTILINE)
    
    # Convert numbered lists (1. 2. 3.) to bullets in Key Ideas section
    text = re.sub(r'^\d+\.\s+', '• ', text, flags=re.MULTILINE)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def parse_answer_sections(raw_answer: str) -> AnswerContent:
    """
    Parse raw LLM answer into structured sections.
    
    Expected format (after normalize_output):
    
    Direct Answer
    [paragraph]
    
    Key Ideas
    • idea 1
    • idea 2
    
    Common Pitfall
    [sentence]
    
    Summary
    [sentence]
    
    Falls back gracefully if structure is missing.
    """
    # First, normalize the output to strip markdown leaks
    text = normalize_output(raw_answer)
    
    lines = text.split('\n')
    
    direct_answer = ""
    key_ideas = []
    common_pitfall = ""
    summary = ""
    
    current_section = None
    
    for line in lines:
        line_stripped = line.strip()
        line_lower = line_stripped.lower()
        
        # Skip empty lines
        if not line_stripped:
            continue
        
        # Detect section headers (strict format - plain text headers)
        if line_lower == 'direct answer' or line_lower.startswith('direct answer:'):
            current_section = 'direct'
            continue
        elif line_lower == 'key ideas' or line_lower.startswith('key ideas:'):
            current_section = 'ideas'
            continue
        elif line_lower == 'common pitfall' or line_lower.startswith('common pitfall:'):
            current_section = 'pitfall'
            continue
        elif line_lower == 'summary' or line_lower.startswith('summary:'):
            current_section = 'summary'
            continue
        
        # Also detect old-style numbered headers (fallback)
        elif '1.' in line_lower and 'direct' in line_lower:
            current_section = 'direct'
            continue
        elif '2.' in line_lower and 'key' in line_lower:
            current_section = 'ideas'
            continue
        elif '3.' in line_lower and 'pitfall' in line_lower:
            current_section = 'pitfall'
            continue
        elif '4.' in line_lower and 'summary' in line_lower:
            current_section = 'summary'
            continue
        
        # Collect content based on current section
        if current_section == 'direct':
            # Direct answer is paragraph text
            if not line_stripped.startswith('•'):
                direct_answer += line_stripped + " "
        elif current_section == 'ideas':
            # Key ideas are bullet points
            if line_stripped.startswith('•'):
                idea = line_stripped.lstrip('• ').strip()
                if idea:
                    key_ideas.append(idea)
            elif line_stripped.startswith(('-', '*')) or (line_stripped[0].isdigit() and '.' in line_stripped[:3]):
                # Fallback for other bullet formats
                idea = line_stripped.lstrip('-•* 0123456789.').strip()
                if idea:
                    key_ideas.append(idea)
        elif current_section == 'pitfall':
            # Common pitfall is one sentence
            if not line_stripped.startswith('•'):
                common_pitfall += line_stripped + " "
        elif current_section == 'summary':
            # Summary is one sentence
            if not line_stripped.startswith('•'):
                summary += line_stripped + " "
    
    # Fallback: if no structure found, use entire answer as direct_answer
    if not direct_answer and not key_ideas:
        direct_answer = text
    
    return AnswerContent(
        direct_answer=direct_answer.strip(),
        key_ideas=key_ideas[:5],  # Max 5 ideas
        common_pitfall=common_pitfall.strip(),
        summary=summary.strip()
    )

# ================================================
# ENDPOINTS
# ================================================

@app.get("/")
def root():
    """Health check"""
    memory_stats = session_store.get_stats()
    return {
        "status": "running",
        "model": MODEL_NAME,
        "vectors": core_store.index.ntotal,
        "llm_provider": actual_provider,
        "version": "3.2.0",
        "features": ["confidence_gating", "conversation_memory", "safety_guards"],
        "memory": memory_stats
    }

@app.get("/health")
def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "llm_provider": actual_provider,
        "cache": {
            "hits": cache_hits,
            "misses": cache_misses,
            "size": len(query_cache)
        },
        "memory": session_store.get_stats()
    }

@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """
    Main query endpoint with confidence gating and conversation memory.
    
    Returns STRICT contract - frontend renders only what's returned.
    """
    global cache_hits, cache_misses
    start_time = time.time()
    
    # =========================================
    # STEP 0: SESSION HANDLING
    # =========================================
    session_id = req.session_id or str(uuid.uuid4())
    memory = session_store.get_or_create(session_id)
    
    print(f"\n{'='*60}")
    print(f"[QUERY] {req.query}")
    print(f"   [SESSION] {session_id[:8]}... (turns: {memory.get_turn_count()})")
    
    # =========================================
    # STEP 1: SAFETY CHECK (before adding to memory)
    # =========================================
    safety_response = get_safety_response(req.query)
    if safety_response:
        print(f"   [MODE] safety - NOT stored in memory")
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Do NOT store unsafe queries in memory
        # Do NOT generate follow-ups for safety responses
        return QueryResponse(
            answer=AnswerContent(
                direct_answer=safety_response["answer"],
                key_ideas=[],
                common_pitfall="",
                summary=""
            ),
            sources=[],
            confidence="low",
            mode="safety",
            latency_ms=latency_ms,
            query=req.query,
            session_id=session_id,
            turn_count=memory.get_turn_count(),
            followups=[],  # No follow-ups for safety
            safety_refusal=True  # IMPORTANT: Frontend must respect this flag
        )
    
    # =========================================
    # STEP 2: ADD USER QUERY TO MEMORY
    # =========================================
    memory.add_turn("user", req.query)
    
    # =========================================
    # STEP 3: CHECK CACHE (include session context in key for multi-turn)
    # =========================================
    # For first turn, use simple cache. For follow-ups, skip cache.
    if memory.get_turn_count() <= 1:
        cache_key = hashlib.md5(f"{req.query}_{req.mode}".encode()).hexdigest()
        if cache_key in query_cache:
            cache_hits += 1
            print(f"   [CACHE HIT]")
            cached = query_cache[cache_key]
            # Update session info in cached response
            cached_dict = cached.dict()
            cached_dict['session_id'] = session_id
            cached_dict['turn_count'] = memory.get_turn_count()
            return QueryResponse(**cached_dict)
    
    cache_misses += 1
    
    try:
        # =========================================
        # STEP 4: RETRIEVE & FILTER
        # =========================================
        raw_results = retrieval_pipeline.retrieve_with_parent_loader(
            query=req.query,
            parent_loader=parent_loader,
            use_longtail=req.use_longtail,
            use_query_rewriting=False
        )
        
        print(f"   [RETRIEVAL] Raw: {len(raw_results)} chunks")
        
        # Filter by score threshold
        filtered_results = filter_by_score(raw_results)
        print(f"   [FILTER] Score threshold: {len(filtered_results)} chunks")
        
        # Apply diversity constraint (one per video)
        diverse_results = apply_diversity_constraint(filtered_results)
        print(f"   [DIVERSITY] One per video: {len(diverse_results)} sources")
        
        # =========================================
        # STEP 5: COMPUTE CONFIDENCE
        # =========================================
        confidence_result = compute_confidence(diverse_results)
        confidence = confidence_result.level
        print(f"   [CONFIDENCE] {confidence.upper()} ({confidence_result.explanation})")
        
        # =========================================
        # STEP 6: GET STRUCTURED MEMORY CONTEXT
        # =========================================
        # Use structured format for proper prompt assembly order
        memory_context = memory.get_structured_context() if memory.get_turn_count() > 1 else {}
        summary_memory = memory_context.get("summary_memory", "")
        recent_turns = memory_context.get("recent_turns", "")
        conversation_context = memory.get_context() if memory.get_turn_count() > 1 else ""  # Legacy fallback
        
        if summary_memory or recent_turns:
            print(f"   [MEMORY] Summary: {len(summary_memory)} chars, Recent: {len(recent_turns)} chars")
        
        # =========================================
        # STEP 7: DETERMINE MODE
        # =========================================
        has_pm_intent = is_pm_intent(req.query)
        use_rag = confidence in ['high', 'medium'] and has_pm_intent
        
        if not use_rag:
            # CONVERSATION MODE
            print(f"   [MODE] conversation")
            
            conv_result = conversational_pm_answer(
                req.query, 
                llm_client,
                conversation_context=conversation_context
            )
            
            # Save assistant response to memory
            memory.add_turn("assistant", conv_result["answer"], query_type="conversation")
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # NO follow-ups for conversation mode (low confidence)
            # Better to show nothing than generic questions
            
            response = QueryResponse(
                answer=AnswerContent(
                    direct_answer=conv_result["answer"],
                    key_ideas=[],
                    common_pitfall="",
                    summary=""
                ),
                sources=[],  # NO sources in conversation mode
                confidence=confidence,
                mode="conversation",
                latency_ms=latency_ms,
                query=req.query,
                session_id=session_id,
                turn_count=memory.get_turn_count(),
                followups=[]  # No generic follow-ups - depth over breadth
            )
            
            return response
        
        # =========================================
        # STEP 8: RAG SYNTHESIS (with memory context)
        # =========================================
        print(f"   [MODE] rag")
        
        # Build sources list
        sources: List[SourceItem] = []
        for chunk in diverse_results:
            youtube_url = retrieval_pipeline.create_deep_link(
                chunk.video_id,
                chunk.start_seconds
            )
            sources.append(SourceItem(
                video_title=getattr(chunk, 'video_title', 'Product Management Podcast'),
                speaker=chunk.speaker or getattr(chunk, 'guest', 'Expert'),
                thumbnail=get_thumbnail_url(chunk.video_id),
                timestamp=format_timestamp(chunk.start_seconds),
                link=youtube_url,
                score=round(chunk.score, 3),
                text_preview=(chunk.text[:150] + "...") if len(chunk.text) > 150 else chunk.text
            ))
        
        # Synthesize answer with structured memory (enables prompt caching)
        if answer_synthesizer:
            result = answer_synthesizer.synthesize(
                query=req.query,
                retrieved_chunks=diverse_results,
                include_citations=True,
                mode=req.mode,
                conversation_context=conversation_context,  # Legacy fallback
                summary_memory=summary_memory,  # Compressed earlier context
                recent_turns=recent_turns  # Last 2 turns
            )
            raw_answer = result['answer']
        else:
            raw_answer = "Retrieval complete. Synthesis unavailable."
        
        # Parse into structured format
        answer = parse_answer_sections(raw_answer)
        
        # Dynamic source limiting based on answer length
        # Rule: Number of citations ≤ logical density of the answer
        limited_sources = limit_sources_by_answer_length(raw_answer, sources)
        print(f"   [SOURCES] Limited to {len(limited_sources)} based on answer length")
        
        # Save assistant response to memory
        memory.add_turn("assistant", answer.direct_answer, query_type="rag")
        
        # =========================================
        # STEP 10: GENERATE SMART FOLLOW-UPS
        # =========================================
        followups = []
        if confidence in ['high', 'medium'] and llm_client:
            try:
                source_topics = extract_source_topics([s.dict() for s in limited_sources])
                followups = generate_followups(
                    user_query=req.query,
                    answer_text=answer.direct_answer,
                    source_topics=source_topics,
                    llm_client=llm_client,
                    confidence=confidence
                )
                print(f"   [FOLLOWUPS] Generated {len(followups)} questions")
            except Exception as e:
                print(f"   [FOLLOWUPS] Error: {e}")
        
        # =========================================
        # STEP 11: MEMORY SUMMARIZATION (if needed)
        # =========================================
        # Uses PM-aware summarization prompt for topic extraction
        if memory.should_summarize() and llm_client:
            try:
                recent = memory.get_recent_turns_for_summary()
                
                # Use GroqLLM's built-in summarization (uses cached PM-aware prompt)
                if hasattr(llm_client, 'summarize_conversation'):
                    new_summary = llm_client.summarize_conversation(
                        previous_summary=memory.memory_summary,
                        recent_turns=recent
                    )
                else:
                    # Fallback to existing method
                    new_summary = summarize_memory(
                        previous_summary=memory.memory_summary,
                        recent_turns=recent,
                        llm_client=llm_client
                    )
                
                memory.update_summary(new_summary)
                print(f"   [MEMORY] Summarized ({len(new_summary)} chars)")
            except Exception as e:
                print(f"   [MEMORY] Summarization failed: {e}")
        
        latency_ms = int((time.time() - start_time) * 1000)
        print(f"   [DONE] {latency_ms}ms")
        
        response = QueryResponse(
            answer=answer,
            sources=limited_sources,
            confidence=confidence,
            mode="rag",
            latency_ms=latency_ms,
            query=req.query,
            session_id=session_id,
            turn_count=memory.get_turn_count(),
            followups=followups
        )
        
        # Cache first-turn responses only
        if memory.get_turn_count() <= 2:
            cache_key = hashlib.md5(f"{req.query}_{req.mode}".encode()).hexdigest()
            query_cache[cache_key] = response
        
        return response
        
    except Exception as e:
        print(f"   [ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Clear a specific session's memory."""
    if session_id in session_store.sessions:
        del session_store.sessions[session_id]
        return {"status": "cleared", "session_id": session_id}
    return {"status": "not_found", "session_id": session_id}

@app.get("/session/{session_id}")
def get_session_info(session_id: str):
    """Get information about a session."""
    if session_id in session_store.sessions:
        memory = session_store.sessions[session_id]
        return {
            "session_id": session_id,
            "turn_count": memory.get_turn_count(),
            "context_preview": memory.get_context()[:500] if memory.get_context() else ""
        }
    return {"status": "not_found", "session_id": session_id}

# ================================================
# STARTUP
# ================================================

@app.on_event("startup")
def startup_event():
    print("\n" + "=" * 70)
    print("[OK] Product Wisdom Hub API running!")
    print("=" * 70)
    print(f"Provider: {actual_provider}")
    print(f"Features: confidence_gating, conversation_memory, safety_guards")
    print("Docs: http://127.0.0.1:8000/docs")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
