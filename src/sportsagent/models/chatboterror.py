from enum import StrEnum
from typing import Any

UNKNOWN_ERROR_RESPONSE = (
    "I'm sorry, but I'm currently unable to generate insights due to a technical issue. "
    "Please try again later."
)


class ErrorStates(StrEnum):
    EMPTY_QUERY = "empty_query"
    NO_DATA_FOUND = "no_data_found"
    VALIDATION_ERROR = "validation_error"
    PARSING_ERROR = "parsing_error"
    CLARIFICATION_NEEDED = "clarification_needed"
    RETRIEVAL_ERROR = "retrieval_error"
    RESPONSE_GENERATION_ERROR = "response_generation_error"
    LLM_RATE_LIMIT = "llm_rate_limit"
    WORKFLOW_ERROR = "workflow_error"
    LLM_TIMEOUT = "llm_timeout"
    UNKNOWN_ERROR = "unknown_error"


class ChatbotError(Exception):
    def __init__(
        self,
        error_type: ErrorStates,
        message: str,
        details: dict[str, Any] | None = None,
        recoverable: bool = True,
    ):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable
        super().__init__(self.message)


class RetrievalError(ChatbotError):
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        recoverable: bool = True,
    ):
        super().__init__(
            error_type=ErrorStates.RETRIEVAL_ERROR,
            message=message,
            details=details,
            recoverable=recoverable,
        )


class ParsingError(ChatbotError):
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        recoverable: bool = True,
    ):
        super().__init__(
            error_type=ErrorStates.PARSING_ERROR,
            message=message,
            details=details,
            recoverable=recoverable,
        )
