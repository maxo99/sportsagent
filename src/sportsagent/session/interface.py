from abc import ABC, abstractmethod

from sportsagent.models.chatbotstate import ChatbotState


class SessionStore(ABC):
    @abstractmethod
    async def get_session(self, session_id: str) -> ChatbotState | None:
        """Retrieve session state by ID"""

    @abstractmethod
    async def save_session(self, session_id: str, state: ChatbotState) -> None:
        """Persist session state"""

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Remove session by ID"""

    @abstractmethod
    async def list_sessions(self) -> list[str]:
        """List all active session IDs"""
