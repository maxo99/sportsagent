
from sportsagent.config import setup_logging
from sportsagent.models.chatbotstate import ChatbotState

logger = setup_logging(__name__)


def exit_node(state: ChatbotState) -> ChatbotState:
    logger.info("Exiting workflow")

    if not state.generated_response:
        state.generated_response = (
            "Unable to generate a response at this time. Please try again later."
        )

    if state.error:
        logger.error(f"Failed workflow with error - {state.error}")
    else:
        logger.info("Successful workflow completion")

    # Update conversation history
    new_turn = {
        "role": "user",
        "content": state.user_query,
        "response": state.generated_response,
        "mentioned_players": state.parsed_query.players if state.parsed_query else [],
        "mentioned_stats": state.parsed_query.statistics if state.parsed_query else [],
        "mentioned_teams": state.parsed_query.teams if state.parsed_query else [],
    }
    state.conversation_history.append(new_turn)

    return state
