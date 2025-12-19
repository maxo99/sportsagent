from sportsagent.config import setup_logging
from sportsagent.models.chatboterror import ErrorStates
from sportsagent.models.chatbotstate import ChatbotState

logger = setup_logging(__name__)


def entry_node(state: ChatbotState) -> ChatbotState:
    logger.info(f"Processing query - state:{state}'")

    if not state.user_query:
        state.error = ErrorStates.EMPTY_QUERY
        state.generated_response = "Please provide a query."
        logger.warning("Empty query received")

    return state
