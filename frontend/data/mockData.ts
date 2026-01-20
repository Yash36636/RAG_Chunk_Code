// API client for Product Wisdom Hub
// Matches STRICT backend contract with session support

export interface AnswerContent {
  direct_answer: string;
  key_ideas: string[];
  common_pitfall: string;
  summary: string;
}

export interface SourceItem {
  video_title: string;
  speaker: string;
  thumbnail: string;
  timestamp: string;
  link: string;
  score: number;
  text_preview: string;
}

export interface QueryResponse {
  answer: AnswerContent;
  sources: SourceItem[];
  confidence: 'low' | 'medium' | 'high';
  mode: 'rag' | 'conversation' | 'safety';
  latency_ms: number;
  query: string;
  session_id: string;
  turn_count: number;
  followups: string[];  // Smart follow-up questions
  safety_refusal: boolean;  // True if query was refused for safety reasons
}

// Backend API URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generate a UUID for session tracking
 */
export function generateSessionId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Query the Product Wisdom Hub API with session support
 */
export async function fetchAnswer(query: string, sessionId?: string): Promise<QueryResponse> {
  const response = await fetch(`${API_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      session_id: sessionId,
      use_longtail: false,
      mode: 'fast'
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Clear a session's conversation memory
 */
export async function clearSession(sessionId: string): Promise<void> {
  await fetch(`${API_URL}/session/${sessionId}`, {
    method: 'DELETE',
  });
}

/**
 * Check if backend is healthy
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
