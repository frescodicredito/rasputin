"""Session management for Rasputin conversations."""

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    id: str
    type: str  # "single" | "council"
    models: list[str]
    messages: dict[str, list[dict]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    total_cost: float = 0.0
    metadata: dict = field(default_factory=dict)

    def add_user_message(self, content: str, model: str | None = None):
        targets = [model] if model else self.models
        for m in targets:
            if m not in self.messages:
                self.messages[m] = []
            self.messages[m].append({"role": "user", "content": content})
        self.last_access = time.time()

    def add_assistant_message(self, model: str, content: str):
        if model not in self.messages:
            self.messages[model] = []
        self.messages[model].append({"role": "assistant", "content": content})
        self.last_access = time.time()

    def get_messages(self, model: str) -> list[dict]:
        return self.messages.get(model, [])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "models": self.models,
            "message_counts": {m: len(msgs) for m, msgs in self.messages.items()},
            "created_at": self.created_at,
            "last_access": self.last_access,
            "total_cost": self.total_cost,
            "age_minutes": round((time.time() - self.created_at) / 60, 1),
        }


class SessionManager:
    def __init__(self, ttl_minutes: int = 120, max_sessions: int = 100):
        self._sessions: dict[str, Session] = {}
        self._ttl = ttl_minutes * 60
        self._max_sessions = max_sessions

    def get_or_create(
        self, session_id: str | None, type: str, models: list[str]
    ) -> Session:
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            if not self._is_expired(session):
                return session

        self._cleanup()
        self._evict_if_needed()

        prefix = "ask" if type == "single" else "council"
        new_id = session_id or f"{prefix}-{uuid.uuid4().hex[:8]}"
        session = Session(id=new_id, type=type, models=models)
        self._sessions[new_id] = session
        return session

    def _evict_if_needed(self):
        """Bound memory: evict least-recently-accessed sessions over the cap."""
        while len(self._sessions) >= self._max_sessions:
            oldest = min(self._sessions.values(), key=lambda s: s.last_access)
            del self._sessions[oldest.id]

    def get(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session and not self._is_expired(session):
            return session
        return None

    def close(self, session_id: str):
        self._sessions.pop(session_id, None)

    def list_active(self) -> list[dict]:
        self._cleanup()
        return [s.to_dict() for s in self._sessions.values()]

    def cleanup_all(self):
        self._sessions.clear()

    def _is_expired(self, session: Session) -> bool:
        return (time.time() - session.last_access) > self._ttl

    def _cleanup(self):
        expired = [sid for sid, s in self._sessions.items() if self._is_expired(s)]
        for sid in expired:
            del self._sessions[sid]
