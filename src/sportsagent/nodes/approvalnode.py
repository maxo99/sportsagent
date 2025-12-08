from sportsagent.config import setup_logging
from sportsagent.models.chatbotstate import ChatbotState

logger = setup_logging(__name__)

def approval_node(state: ChatbotState) -> ChatbotState:
    """
    A pass-through node that serves as an interruption point for human approval.
    """
    logger.info("Approval node reached. Waiting for human input if configured.")
    return state
