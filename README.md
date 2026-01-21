# Lenny's Podcast Second Brain

> A product-management-focused conversational RAG system that synthesizes insights from 100+ hours of Lenny's Podcast conversations with top product leaders.

![Version](https://img.shields.io/badge/version-4.0.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![License](https://img.shields.io/badge/license-MIT-gray)

**🔗 Live Demo:** [Coming Soon]

---

## 🎯 What This Is

**Lenny's Podcast Second Brain** is an AI-powered knowledge system that:

- Answers product management questions using **real expert conversations**
- Shows **confidence levels** based on source quality (not guessing)
- Provides **clickable citations** to original YouTube timestamps
- Generates **depth-building follow-ups** like a senior PM mentor
- Gracefully handles off-topic or unsafe queries

**This is NOT a general chatbot.** It's a grounded knowledge system that only speaks with authority when it has strong evidence.

---

## 🧠 Key Design Decisions

### 1. Confidence Gating (Most Important)

**Problem:** LLMs confidently hallucinate when they don't know.

**Solution:** We compute confidence from FAISS retrieval scores *before* synthesis. Low confidence = we change behavior.

| Confidence | Behavior |
|------------|----------|
| **High** (≥0.65) | Authoritative answer with citations |
| **Medium** (≥0.52) | Balanced insights, acknowledge limitations |
| **Low** (<0.52) | Mentor-style conversation, no false authority |

### 2. Depth-Building Follow-ups

**Problem:** Generic follow-ups like "Tell me more?" feel like a support chatbot.

**Solution:** Follow-ups are generated from:
- The answer just given
- Themes from retrieved sources
- A "senior PM mentor" prompt

Result: Questions that push deeper thinking, not generic probing.

### 3. Source Diversity Constraint

**Problem:** Top results might all be from the same video, creating echo-chamber answers.

**Solution:** Max one citation per video. Forces diversity in perspectives.

### 4. Frontend Never Fabricates

**Problem:** Client-side fallbacks can show fake citations.

**Solution:** Frontend renders ONLY what backend returns. Zero client-side generation.

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌─────────────────┐
│  Safety Check   │ ──→ Block harmful queries
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FAISS Retrieval │ ──→ Find similar chunks (score ≥ 0.60)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Confidence Gate │ ──→ HIGH/MEDIUM → RAG Mode
└────────┬────────┘      LOW → Conversation Mode
         │
         ▼
┌─────────────────┐
│ LLM Synthesis   │ ──→ Groq (fast) / Ollama (local)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Follow-up Gen   │ ──→ Only if confidence ≥ MEDIUM
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Strict Response │ ──→ { answer, sources, confidence, followups }
└─────────────────┘
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.9+
- Node.js 18+
- [Groq API key](https://console.groq.com) (free)

### Backend

```bash
cd RAG_Chunk_Code

# Install dependencies
pip install -r requirements.txt

# Set Groq API key
export GROQ_API_KEY=your_key_here  # Mac/Linux
$env:GROQ_API_KEY="your_key_here"  # Windows PowerShell

# Start server
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:3000**

---

## ☁️ Hosting (Production)

### Backend → Render

1. Push repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Configure:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Environment variables:** `GROQ_API_KEY=your_key`, `LLM_PROVIDER=groq`

Or use the included `render.yaml` for one-click deploy.

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repo
3. Set root directory to `frontend/`
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL=https://your-backend.onrender.com`
5. Deploy

---

## 📊 API Reference

### POST /query

```json
// Request
{
  "query": "What makes a great product manager?",
  "session_id": "optional-uuid"
}

// Response
{
  "answer": {
    "direct_answer": "...",
    "key_ideas": ["...", "..."],
    "common_pitfall": "...",
    "summary": "..."
  },
  "sources": [
    {
      "video_title": "Episode with Shreyas Doshi",
      "speaker": "Shreyas Doshi",
      "thumbnail": "https://img.youtube.com/vi/xxx/mqdefault.jpg",
      "timestamp": "14:32",
      "link": "https://youtube.com/watch?v=xxx&t=872",
      "score": 0.72
    }
  ],
  "confidence": "high",
  "mode": "rag",
  "followups": [
    "Which of these traits is hardest to develop early in a PM career?",
    "How would you demonstrate accountability when you don't own execution?"
  ],
  "latency_ms": 1200
}
```

---

## 📁 Project Structure

```
RAG_Chunk_Code/
├── server.py                 # FastAPI entry point
├── src/
│   ├── confidence.py         # Confidence scoring (≥0.60 threshold)
│   ├── safety.py             # Safety guards
│   ├── followup_generator.py # Depth-building follow-ups
│   ├── unified_synthesizer.py
│   ├── retrieval.py          # FAISS search
│   ├── memory.py             # Session memory
│   ├── prompts/
│   │   └── cached_system.py  # Static prompts (Groq caching)
│   └── llm/
│       ├── groq_llm.py       # Groq client
│       └── ollama_llm.py     # Ollama client
├── frontend/
│   ├── app/page.tsx          # Main chat UI
│   ├── components/
│   │   ├── AnswerPanel.tsx   # Structured answer display
│   │   ├── CitationSidebar.tsx
│   │   └── ...
│   └── data/mockData.ts      # API client
├── faiss_indexes/            # Vector embeddings
├── chunks_product_management/ # Source transcripts
├── render.yaml               # Render deployment config
└── requirements.txt
```

---
