from typing import Annotated, Any, Literal

from IPython.display import Markdown
from pydantic import BaseModel, Field, StringConstraints

from sportsagent.models.chatboterror import ErrorStates
from sportsagent.models.parsedquery import ParsedQuery

type ConversationHistory = list[dict[str, Any]]
type PendingAction = Literal["retrieve", "enrich", "rechart"]
type ApprovalResult = Literal["approved", "denied"]


class RetrievedData(BaseModel):
    players: list[dict[str, Any]] = Field(default_factory=list)
    teams: list[dict[str, Any]] = Field(default_factory=list)
    extra: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)

    def items(self):
        """Iterate over non-empty datasets."""
        if self.players:
            yield "players", self.players
        if self.teams:
            yield "teams", self.teams
        for key, value in self.extra.items():
            if value:
                yield key, value

    def keys(self):
        """Return keys of non-empty datasets."""
        keys = []
        if self.players:
            keys.append("players")
        if self.teams:
            keys.append("teams")
        keys.extend([k for k, v in self.extra.items() if v])
        return keys

    def __len__(self):
        """Return number of non-empty datasets."""
        return (
            (1 if self.players else 0)
            + (1 if self.teams else 0)
            + sum(1 for v in self.extra.values() if v)
        )

    def add_player_data(self, data: list[dict[str, Any]]) -> None:
        self.players.extend(data)

    def add_team_data(self, data: list[dict[str, Any]]) -> None:
        self.teams.extend(data)

    def set_dataset(self, key: str, data: list[dict[str, Any]]) -> None:
        self.extra[key] = data

    def add_to_dataset(self, key: str, data: list[dict[str, Any]]) -> None:
        self.extra.setdefault(key, []).extend(data)


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
