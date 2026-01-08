import asyncio

from sportsagent.config import setup_logging
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.session.interface import SessionStore

logger = setup_logging(__name__)


class InMemorySessionStore(SessionStore):
    def __init__(self):
        self._store: dict[str, ChatbotState] = {}
        self._lock = asyncio.Lock()

    async def get_session(self, session_id: str) -> ChatbotState | None:
        try:
            async with self._lock:
                return self._store.get(session_id)
        except Exception as exc:
            logger.error(f"Failed to get session {session_id}: {exc}")
            raise

    async def save_session(self, session_id: str, state: ChatbotState) -> None:
        try:
            async with self._lock:
                self._store[session_id] = state
        except Exception as exc:
            logger.error(f"Failed to save session {session_id}: {exc}")
            raise

    async def delete_session(self, session_id: str) -> None:
        try:
            async with self._lock:
                self._store.pop(session_id, None)
        except Exception as exc:
            logger.error(f"Failed to delete session {session_id}: {exc}")
            raise

    async def list_sessions(self) -> list[str]:
        try:
            async with self._lock:
                return list(self._store.keys())
        except Exception as exc:
            logger.error(f"Failed to list sessions: {exc}")
            raise
