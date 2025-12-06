from typing import Annotated, Any

import pandas as pd
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field, StringConstraints

from sportsagent.models.chatboterror import ErrorStates
from sportsagent.models.parsedquery import ParsedQuery

type ConversationHistory = list[dict[str, Any]]


class ChatbotState(BaseModel):
    session_id: str
    user_query: Annotated[str, StringConstraints(strip_whitespace=True)]
    messages: list[BaseMessage] = Field(default_factory=list)
    parsed_query: ParsedQuery | None = Field(default=None)
    retrieved_data: pd.DataFrame | None = Field(default=None)
    generated_response: str
    conversation_history: ConversationHistory = Field(default_factory=list)
    error: ErrorStates | None = Field(default=None)

    def __str__(self) -> str:
        return (
            f"ChatbotState(session_id={self.session_id}, "
            f"user_query={self.user_query[:20]}..., "
            f"parsed_query={self.parsed_query}, "
            f"generated_response={self.generated_response[:20]}..., "
            f"error={self.error})"
        )
