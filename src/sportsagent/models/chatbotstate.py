from typing import Annotated, Any, Literal

from IPython.display import Markdown
from pydantic import BaseModel, Field, StringConstraints

from sportsagent.models.chatboterror import ErrorStates
from sportsagent.models.parsedquery import ParsedQuery
from sportsagent.models.retrieveddata import RetrievedData

type ConversationHistory = list[dict[str, Any]]
type PendingAction = Literal["retrieve", "enrich", "rechart"]
type ApprovalResult = Literal["approved", "denied"]



class ChatbotState(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
    }
    session_id: str
    user_query: Annotated[str, StringConstraints(strip_whitespace=True)]
    parsed_query: ParsedQuery = Field(default_factory=ParsedQuery)
    generated_response: str | Markdown
    conversation_history: ConversationHistory = Field(default_factory=list)
    error: ErrorStates | None = Field(default=None)
    retrieved_data: RetrievedData | None = Field(default=None)
    pending_action: PendingAction | None = Field(default=None)
    approval_required: bool = Field(default=False)
    approval_result: ApprovalResult | None = Field(default=None)
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

    @property
    def pq(self) -> ParsedQuery:
        if self.parsed_query is None:
            self.error = ErrorStates.PARSING_ERROR
            self.generated_response = "No parsed query available for data retrieval."
            raise ValueError("parsed_query is None")
        return self.parsed_query
