"""Conversation context cache with Redis-first storage."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import redis
except ModuleNotFoundError:  # pragma: no cover - optional dependency in some test environments
    redis = None

from config import settings

logger = logging.getLogger(__name__)
_MISSING = object()


class MemoryCache:
    """In-memory cache fallback used in tests and when Redis is unavailable."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def connect(self):
        logger.info("Initialized in-memory cache fallback")

    def disconnect(self):
        self._cache.clear()

    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        payload = self._cache.get(f"session:{session_id}:context")
        if not payload:
            return None
        return self._normalize_context(payload)

    def update_context(
        self,
        session_id: str,
        history: Optional[List[Dict]] = None,
        user_profile: Optional[Dict] = None,
        last_intent: Optional[str] = None,
        intent_history: Optional[List[Dict]] = None,
        conversation_summary: Optional[str] = None,
        last_quick_actions: Optional[List[Dict]] = None,
        active_task: Any = _MISSING,
        task_stack: Any = _MISSING,
        pending_question: Any = _MISSING,
        pending_action: Any = _MISSING,
    ):
        key = f"session:{session_id}:context"
        existing = self._cache.get(key, {})
        if history is not None:
            existing["history"] = history
        if user_profile is not None:
            existing["user_profile"] = user_profile
        if last_intent is not None:
            existing["last_intent"] = last_intent
        if intent_history is not None:
            existing["intent_history"] = intent_history
        if conversation_summary is not None:
            existing["conversation_summary"] = conversation_summary
        if last_quick_actions is not None:
            existing["last_quick_actions"] = last_quick_actions
        if active_task is not _MISSING:
            existing["active_task"] = active_task
        if task_stack is not _MISSING:
            existing["task_stack"] = task_stack
        if pending_question is not _MISSING:
            existing["pending_question"] = pending_question
        if pending_action is not _MISSING:
            existing["pending_action"] = pending_action
        existing["updated_at"] = datetime.now().isoformat()
        self._cache[key] = existing

    def clear_context(self, session_id: str):
        self._cache.pop(f"session:{session_id}:context", None)

    def add_message_to_context(self, session_id: str, user_message: str, assistant_message: str):
        key = f"session:{session_id}:context"
        existing = self._cache.get(key, {})
        history = list(existing.get("history", []))
        history.append(
            {
                "user": user_message,
                "assistant": assistant_message,
                "timestamp": datetime.now().isoformat(),
            }
        )
        existing["history"] = history[-settings.CONTEXT_MAX_HISTORY :]
        existing["updated_at"] = datetime.now().isoformat()
        self._cache[key] = existing

    def get(self, key: str) -> Optional[str]:
        value = self._cache.get(key)
        if value is None:
            return None
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)

    def set(self, key: str, value: str, expire: Optional[int] = None):
        self._cache[key] = value

    def delete(self, key: str):
        self._cache.pop(key, None)

    @staticmethod
    def _normalize_context(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "history": data.get("history", []),
            "user_profile": data.get("user_profile", {}),
            "last_intent": data.get("last_intent"),
            "intent_history": data.get("intent_history", []),
            "conversation_summary": data.get("conversation_summary", ""),
            "last_quick_actions": data.get("last_quick_actions", []),
            "active_task": data.get("active_task"),
            "task_stack": data.get("task_stack", []),
            "pending_question": data.get("pending_question"),
            "pending_action": data.get("pending_action"),
            "updated_at": data.get("updated_at"),
        }


class RedisCache:
    """Use Redis when available and fall back to in-memory cache otherwise."""

    def __init__(self):
        self._client: redis.Redis | None = None
        self._memory = MemoryCache()
        self._connected = False

    def connect(self):
        self._memory.connect()
        if redis is None:
            if settings.REDIS_REQUIRED:
                raise RuntimeError("redis package is required when REDIS_REQUIRED=true")
            logger.warning("redis package is unavailable, using in-memory context cache")
            return
        try:
            self._client = redis.from_url(settings.redis_url, decode_responses=True)
            self._client.ping()
            self._connected = True
            logger.info("Connected to Redis context cache")
        except Exception as exc:
            self._client = None
            self._connected = False
            if settings.REDIS_REQUIRED:
                raise
            logger.warning("Redis unavailable, using in-memory context cache: %s", exc)

    def disconnect(self):
        if self._client is not None:
            self._client.close()
        self._client = None
        self._connected = False
        self._memory.disconnect()

    def _context_key(self, session_id: str) -> str:
        return f"session:{session_id}:context"

    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not self._connected or self._client is None:
            return self._memory.get_context(session_id)

        raw = self._client.get(self._context_key(session_id))
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to decode Redis context for session=%s", session_id)
            return None
        return MemoryCache._normalize_context(data)

    def update_context(
        self,
        session_id: str,
        history: Optional[List[Dict]] = None,
        user_profile: Optional[Dict] = None,
        last_intent: Optional[str] = None,
        intent_history: Optional[List[Dict]] = None,
        conversation_summary: Optional[str] = None,
        last_quick_actions: Optional[List[Dict]] = None,
        active_task: Any = _MISSING,
        task_stack: Any = _MISSING,
        pending_question: Any = _MISSING,
        pending_action: Any = _MISSING,
    ):
        if not self._connected or self._client is None:
            self._memory.update_context(
                session_id=session_id,
                history=history,
                user_profile=user_profile,
                last_intent=last_intent,
                intent_history=intent_history,
                conversation_summary=conversation_summary,
                last_quick_actions=last_quick_actions,
                active_task=active_task,
                task_stack=task_stack,
                pending_question=pending_question,
                pending_action=pending_action,
            )
            return

        existing = self.get_context(session_id) or {}
        if history is not None:
            existing["history"] = history
        if user_profile is not None:
            existing["user_profile"] = user_profile
        if last_intent is not None:
            existing["last_intent"] = last_intent
        if intent_history is not None:
            existing["intent_history"] = intent_history
        if conversation_summary is not None:
            existing["conversation_summary"] = conversation_summary
        if last_quick_actions is not None:
            existing["last_quick_actions"] = last_quick_actions
        if active_task is not _MISSING:
            existing["active_task"] = active_task
        if task_stack is not _MISSING:
            existing["task_stack"] = task_stack
        if pending_question is not _MISSING:
            existing["pending_question"] = pending_question
        if pending_action is not _MISSING:
            existing["pending_action"] = pending_action
        existing["updated_at"] = datetime.now().isoformat()
        self._client.set(
            self._context_key(session_id),
            json.dumps(existing, ensure_ascii=False),
            ex=settings.CONTEXT_CACHE_TTL_SECONDS,
        )

    def clear_context(self, session_id: str):
        if not self._connected or self._client is None:
            self._memory.clear_context(session_id)
            return
        self._client.delete(self._context_key(session_id))

    def add_message_to_context(self, session_id: str, user_message: str, assistant_message: str):
        context = self.get_context(session_id) or {}
        history = list(context.get("history", []))
        history.append(
            {
                "user": user_message,
                "assistant": assistant_message,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self.update_context(session_id=session_id, history=history[-settings.CONTEXT_MAX_HISTORY :])

    def get(self, key: str) -> Optional[str]:
        if not self._connected or self._client is None:
            return self._memory.get(key)
        return self._client.get(key)

    def set(self, key: str, value: str, expire: Optional[int] = None):
        if not self._connected or self._client is None:
            self._memory.set(key, value, expire=expire)
            return
        self._client.set(key, value, ex=expire)

    def delete(self, key: str):
        if not self._connected or self._client is None:
            self._memory.delete(key)
            return
        self._client.delete(key)


redis_cache = RedisCache()
