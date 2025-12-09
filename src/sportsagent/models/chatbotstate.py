from typing import Annotated, Any

from IPython.display import Markdown
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field, StringConstraints

from sportsagent.models.chatboterror import ErrorStates
from sportsagent.models.parsedquery import ParsedQuery

type ConversationHistory = list[dict[str, Any]]


class ChatbotState(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
    }
    session_id: str
    user_query: Annotated[str, StringConstraints(strip_whitespace=True)]
    messages: list[BaseMessage] = Field(default_factory=list)
    parsed_query: ParsedQuery | None = Field(default=None)
    generated_response: str | Markdown
    conversation_history: ConversationHistory = Field(default_factory=list)
    error: ErrorStates | None = Field(default=None)
    retrieved_data: list[dict[str, Any]] | None = Field(default=None)
    needs_visualization: bool = Field(default=False)
    visualization_code: str | None = Field(default=None)
    visualization: Any | None = Field(default=None)
    internal_trace: list[str] = Field(default_factory=list)
    skip_save: bool = Field(default=False)

    def __str__(self) -> str:
        return (
            f"ChatbotState(session_id={self.session_id}, "
            f"user_query={self.user_query[:20]}..., "
            f"parsed_query={self.parsed_query}, "
            f"generated_response={str(self.generated_response)[:20]}..., "
            f"error={self.error})"
        )
