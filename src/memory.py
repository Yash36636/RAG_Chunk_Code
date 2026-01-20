"""
Session-Scoped Conversation Memory
Preserves context during chat sessions without polluting FAISS or embeddings

Key Design Decisions:
- In-memory storage (no persistence across restarts)
- TTL-based cleanup (sessions expire after inactivity)
- Max turns limit (prevents context bloat)
- Safety: unsafe queries are NOT stored
"""

import time
from collections import deque
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class MemoryTurn:
    """Single turn in conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    query_type: Optional[str] = None  # "rag", "conversation", "safety"


class ConversationMemory:
    """
    Session-scoped memory for multi-turn conversations.
    
    Features:
    - Sliding window of recent turns
    - Topic-aware memory summarization
    - PM-focused context compression
    """
    
    # Summarization threshold
    SUMMARIZE_AFTER_TURNS = 4  # Summarize after every 4 turns
    
    def __init__(self, max_turns: int = 8):
        """
        Initialize conversation memory.
        
        Args:
            max_turns: Maximum number of turns to keep (older ones are dropped)
        """
        self.history: deque[MemoryTurn] = deque(maxlen=max_turns)
        self.created_at = time.time()
        self.last_activity = time.time()
        self.current_topic: Optional[str] = None  # Detected PM topic
        self.memory_summary: str = ""  # Compressed topic-aware summary
        self.turns_since_summary: int = 0
    
    def add_turn(self, role: str, content: str, query_type: Optional[str] = None):
        """
        Add a turn to the conversation.
        
        Args:
            role: "user" or "assistant"
            content: The message content
            query_type: Type of query ("rag", "conversation", "safety")
        """
        self.history.append(MemoryTurn(
            role=role,
            content=content,
            query_type=query_type
        ))
        self.last_activity = time.time()
        self.turns_since_summary += 1
    
    def needs_summarization(self) -> bool:
        """Check if memory should be summarized."""
        return self.turns_since_summary >= self.SUMMARIZE_AFTER_TURNS
    
    def get_recent_turns_for_summary(self, count: int = 4) -> str:
        """Get recent turns formatted for summarization."""
        recent = list(self.history)[-count:]
        lines = []
        for turn in recent:
            prefix = "User" if turn.role == "user" else "Assistant"
            content = turn.content[:300] if len(turn.content) > 300 else turn.content
            lines.append(f"{prefix}: {content}")
        return "\n".join(lines)
    
    def update_summary(self, new_summary: str):
        """Update the memory summary after LLM summarization."""
        self.memory_summary = new_summary
        self.turns_since_summary = 0
    
    def get_pm_context(self) -> str:
        """
        Get PM-focused context for prompt injection.
        Returns summary + recent turns.
        """
        parts = []
        
        if self.memory_summary:
            parts.append(f"Previous Discussion Summary:\n{self.memory_summary}")
        
        # Add last 2 turns for immediate context
        recent = list(self.history)[-2:]
        if recent:
            recent_text = []
            for turn in recent:
                prefix = "User" if turn.role == "user" else "Assistant"
                content = turn.content[:200] if len(turn.content) > 200 else turn.content
                recent_text.append(f"{prefix}: {content}")
            parts.append(f"Recent:\n" + "\n".join(recent_text))
        
        return "\n\n".join(parts) if parts else ""
    
    def get_structured_context(self) -> Dict[str, str]:
        """
        Get conversation context in structured format for prompt assembly.
        
        Returns:
            Dict with:
            - summary_memory: Compressed summary of earlier conversation
            - recent_turns: Last 2 turns as formatted string
        """
        # Get summary
        summary = self.memory_summary or ""
        
        # Get last 2 turns (excluding the current query being processed)
        recent = list(self.history)[-3:-1] if len(self.history) > 1 else []
        recent_text = ""
        
        if recent:
            lines = []
            for turn in recent:
                prefix = "User" if turn.role == "user" else "Assistant"
                content = turn.content[:250] if len(turn.content) > 250 else turn.content
                lines.append(f"{prefix}: {content}")
            recent_text = "\n".join(lines)
        
        return {
            "summary_memory": summary,
            "recent_turns": recent_text
        }
    
    def should_summarize(self) -> bool:
        """
        Check if memory should be summarized.
        
        Triggers summarization when:
        - More than 3 turns since last summary
        - OR total turns > 6 and no summary yet
        """
        if self.turns_since_summary >= 3:
            return True
        if len(self.history) > 6 and not self.memory_summary:
            return True
        return False
    
    def get_context(self, max_chars: int = 1500) -> str:
        """
        Returns compressed conversation context for prompt injection.
        
        Args:
            max_chars: Maximum characters for context (prevents prompt bloat)
            
        Returns:
            Formatted conversation history string
        """
        if not self.history:
            return ""
        
        context_lines = []
        total_chars = 0
        
        # Build from most recent, then reverse
        for turn in reversed(list(self.history)):
            prefix = "User" if turn.role == "user" else "Assistant"
            
            # Truncate long messages
            content = turn.content
            if len(content) > 300:
                content = content[:300] + "..."
            
            line = f"{prefix}: {content}"
            
            if total_chars + len(line) > max_chars:
                break
                
            context_lines.insert(0, line)
            total_chars += len(line) + 1
        
        return "\n".join(context_lines)
    
    def get_last_user_query(self) -> Optional[str]:
        """Get the most recent user query."""
        for turn in reversed(list(self.history)):
            if turn.role == "user":
                return turn.content
        return None
    
    def get_turn_count(self) -> int:
        """Get number of turns in memory."""
        return len(self.history)
    
    def clear(self):
        """Clear all memory."""
        self.history.clear()
        self.current_topic = None


class SessionStore:
    """
    Global session store with automatic cleanup.
    
    Features:
    - Session creation and retrieval
    - TTL-based expiration
    - Memory usage bounds
    """
    
    # Configuration
    SESSION_EXPIRY_SECONDS = 30 * 60  # 30 minutes
    MAX_SESSIONS = 1000  # Prevent memory bloat
    CLEANUP_INTERVAL = 5 * 60  # Cleanup every 5 minutes
    
    def __init__(self):
        self.sessions: Dict[str, ConversationMemory] = {}
        self.last_cleanup = time.time()
    
    def get_or_create(self, session_id: str) -> ConversationMemory:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            ConversationMemory for this session
        """
        # Periodic cleanup
        if time.time() - self.last_cleanup > self.CLEANUP_INTERVAL:
            self._cleanup_expired()
        
        if session_id not in self.sessions:
            # Enforce max sessions
            if len(self.sessions) >= self.MAX_SESSIONS:
                self._cleanup_oldest()
            
            self.sessions[session_id] = ConversationMemory()
        
        return self.sessions[session_id]
    
    def _cleanup_expired(self):
        """Remove sessions that have been inactive too long."""
        now = time.time()
        expired = [
            sid for sid, memory in self.sessions.items()
            if now - memory.last_activity > self.SESSION_EXPIRY_SECONDS
        ]
        
        for sid in expired:
            del self.sessions[sid]
        
        if expired:
            print(f"   [MEMORY] Cleaned up {len(expired)} expired sessions")
        
        self.last_cleanup = now
    
    def _cleanup_oldest(self):
        """Remove oldest sessions to make room."""
        if not self.sessions:
            return
        
        # Sort by last activity, remove oldest 10%
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_activity
        )
        
        to_remove = max(1, len(sorted_sessions) // 10)
        for sid, _ in sorted_sessions[:to_remove]:
            del self.sessions[sid]
        
        print(f"   [MEMORY] Cleaned up {to_remove} oldest sessions (at capacity)")
    
    def get_stats(self) -> Dict:
        """Get memory usage statistics."""
        return {
            "active_sessions": len(self.sessions),
            "max_sessions": self.MAX_SESSIONS,
            "expiry_minutes": self.SESSION_EXPIRY_SECONDS // 60
        }


# Global session store instance
session_store = SessionStore()
