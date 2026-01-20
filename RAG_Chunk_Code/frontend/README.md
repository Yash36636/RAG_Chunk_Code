# Lenny's Podcast Second Brain — Frontend

Next.js chat interface for the Product Management RAG system.

## Quick Start

```bash
npm install
npm run dev
```

Visit http://localhost:3000

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## Deploy to Vercel

1. Import this repo to Vercel
2. Set root directory to `frontend/`
3. Add environment variable: `NEXT_PUBLIC_API_URL=https://your-backend.onrender.com`
4. Deploy

## Tech Stack

- **Next.js 14** (App Router)
- **React 18**
- **Tailwind CSS**
- **Lucide Icons**

## Key Components

| Component | Purpose |
|-----------|---------|
| `AnswerPanel` | Displays structured RAG answers |
| `CitationSidebar` | Shows source cards with YouTube thumbnails |
| `ConfidenceBadge` | Visual confidence indicator |
| `ChatInput` | User query input |
| `ProductWisdomHeader` | Branded header with logo |

## Design Principles

1. **Frontend Never Fabricates** — Renders only what backend returns
2. **Confidence-Aware UI** — Different styling for high/medium/low confidence
3. **Citation-First** — Sources are prominently displayed, not hidden
4. **Mobile-Responsive** — Works on all screen sizes
