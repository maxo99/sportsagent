import uuid

from sportsagent.config import setup_logging
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.session.interface import SessionStore

logger = setup_logging(__name__)


class SessionManager:
    def __init__(self, store: SessionStore):
        self._store = store

    async def get_or_create_session(self, session_id: str | None) -> ChatbotState:
        try:
            target_session_id = session_id or str(uuid.uuid4())
            state = await self._store.get_session(target_session_id)

            if state is None:
                state = ChatbotState(
                    session_id=target_session_id,
                    user_query="",  # Will be set when query is processed
                    generated_response="",
                )
                await self._store.save_session(target_session_id, state)

            return state
        except Exception as exc:
            logger.error(f"Failed to get or create session: {exc}")
            raise

    async def save_session(self, state: ChatbotState) -> None:
        try:
            await self._store.save_session(state.session_id, state)
        except Exception as exc:
            logger.error(f"Failed to save session {state.session_id}: {exc}")
            raise

    async def delete_session(self, session_id: str) -> None:
        try:
            await self._store.delete_session(session_id)
        except Exception as exc:
            logger.error(f"Failed to delete session {session_id}: {exc}")
            raise

    async def list_sessions(self) -> list[str]:
        try:
            return await self._store.list_sessions()
        except Exception as exc:
            logger.error(f"Failed to list sessions: {exc}")
            raise
