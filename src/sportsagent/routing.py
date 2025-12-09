from typing import Literal

from sportsagent.config import setup_logging
from sportsagent.models.chatboterror import ErrorStates
from sportsagent.models.chatbotstate import ChatbotState

logger = setup_logging(__name__)


def should_continue_after_entry(state: ChatbotState) -> Literal["query_parser", "exit"]:
    # Check for errors in entry node
    if state.error == ErrorStates.EMPTY_QUERY:
        logger.info("Entry -> Exit (empty query)")
        return "exit"

    logger.info("Entry -> Query Parser")
    return "query_parser"


def should_continue_after_parser(state: ChatbotState) -> Literal["retriever", "exit"]:
    # Check for parsing errors
    if state.error and "query_parser" in state.error:
        logger.info("Query Parser -> Exit (parsing error)")
        return "exit"

    # Check if clarification is needed
    if state.error == "clarification_needed":
        logger.info("Query Parser -> Exit (clarification needed)")
        return "exit"

    # Check if query was parsed successfully
    if not state.parsed_query:
        logger.warning("Query Parser -> Exit (no parsed query)")
        state.error = ErrorStates.PARSING_ERROR
        state.generated_response = "I couldn't understand your question. Please try rephrasing it."
        return "exit"

    logger.info("Query Parser -> Retriever")
    return "retriever"


def should_continue_after_retriever(state: ChatbotState) -> Literal["analyzer", "exit"]:
    # Check for retrieval errors
    if state.error and "retriever" in state.error:
        logger.info("Retriever -> Exit (retrieval error)")
        return "exit"

    # Check if data was retrieved
    retrieved_data = state.retrieved_data
    if retrieved_data is None or len(retrieved_data) == 0:
        logger.info("Retriever -> Exit (no data)")
        if not state.generated_response:
            state.generated_response = (
                "I couldn't find any statistics matching your query. "
                "Please check the player name and time period."
            )
        return "exit"

    logger.info("Retriever -> analyzer")
    return "analyzer"


# def should_continue_after_analyzer(state: ChatbotState) -> Literal["memory", "exit"]:
#     # Check for analyzer errors
#     if state.error and "analyzer" in state.error:
#         logger.warning("analyzer -> Memory (with error, but continuing)")
#         # Continue to memory even with errors to maintain conversation history
#         return "memory"

#     # Check if response was generated
#     if not state.generated_response:
#         logger.warning("analyzer -> Exit (no response generated)")
#         state.generated_response = "I couldn't generate a response. Please try again."
#         return "exit"

#     logger.info("analyzer -> Memory")
#     return "memory"


def should_continue_after_analyzer(
    state: ChatbotState,
) -> Literal["approval", "generate_visualization", "save_report", "exit"]:
    # Check for routing signal
    if state.generated_response and state.generated_response.startswith("__ROUTE_TO_RETRIEVER__"):
        logger.info("Analyzer -> Approval (request more data)")
        # Clean up the response before routing
        # The query is already in state.user_query
        state.generated_response = ""
        return "approval"

    if state.needs_visualization:
        logger.info("Analyzer -> Generate Visualization")
        return "generate_visualization"

    logger.info("Analyzer -> Save Report")
    return "save_report"
