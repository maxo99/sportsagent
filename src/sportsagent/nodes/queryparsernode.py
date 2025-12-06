import asyncio
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from sportsagent import utils
from sportsagent.config import setup_logging
from sportsagent.constants import CURRENT_SEASON
from sportsagent.datasource.nflreadpy import normalize_stat_names, normalize_team_names
from sportsagent.models.chatboterror import ChatbotError, ErrorStates
from sportsagent.models.chatbotstate import ChatbotState, ConversationHistory
from sportsagent.models.parsedquery import ParsedQuery

logger = setup_logging(__name__)


def query_parser_node(state: ChatbotState) -> ChatbotState:
    logger.info("Parsing user query")

    try:
        state = _parse_query_sync(state)
        logger.info(
            f"Successfully parsed query.intent - {state.parsed_query.query_intent if state.parsed_query else 'unknown'}"
        )
    except ChatbotError as e:
        state.error = e.error_type
        state.generated_response = e.message
    except Exception as e:
        logger.warning(f"Unexpected error during query parsing: {e}")
        state.error = ErrorStates.PARSING_ERROR
        state.generated_response = "An unexpected error occurred while parsing your query."
        # raise e
    return state


def _parse_query_sync(state: ChatbotState) -> ChatbotState:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_parse_query(state))


def _extract_context_from_history(
    conversation_history: ConversationHistory,
) -> dict[str, Any]:
    context = {
        "recent_players": [],
        "recent_stats": [],
        "recent_teams": [],
    }

    # Look at last 3 turns for context
    recent_turns = (
        conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
    )

    for turn in recent_turns:
        if "mentioned_players" in turn:
            context["recent_players"].extend(turn["mentioned_players"])
        if "mentioned_stats" in turn:
            context["recent_stats"].extend(turn["mentioned_stats"])

    # Remove duplicates while preserving order
    context["recent_players"] = list(dict.fromkeys(context["recent_players"]))
    context["recent_stats"] = list(dict.fromkeys(context["recent_stats"]))

    return context


def _build_parsing_prompt(user_query: str, context: dict[str, Any]) -> str:
    prompt = utils.get_prompt_template("parsing_prompt.j2").render(
        current_season=CURRENT_SEASON,
    )

    if context["recent_players"] or context["recent_stats"]:
        prompt += "\n\n**CONVERSATION CONTEXT (Use this to resolve references):**"

        if context["recent_players"]:
            prompt += f"\n- Recently mentioned players: {', '.join(context['recent_players'])}"
            prompt += "\n  → If the query doesn't mention a player explicitly, assume it refers to these players"

        if context["recent_stats"]:
            prompt += f"\n- Recently mentioned statistics: {', '.join(context['recent_stats'])}"
            prompt += "\n  → If the query asks about 'those stats' or similar, use these"

        prompt += "\n\n**This appears to be a follow-up question. Use the context above to fill in missing information.**"

    prompt += utils.get_prompt_template("ambiguity_handling.j2").render(
        user_query=user_query,
    )
    return prompt


async def _parse_query(state: ChatbotState) -> ChatbotState:
    try:
        user_query = state.user_query
        conversation_history = state.conversation_history

        context = _extract_context_from_history(conversation_history)

        system_prompt = _build_parsing_prompt(user_query, context)

        llm = ChatOpenAI(
            model="gpt-4",
        )

        structured_llm = llm.with_structured_output(ParsedQuery)

        parsed_result = structured_llm.invoke(
            input=[
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_query),
            ],
            temperature=0,
        )
        if not isinstance(parsed_result, ParsedQuery):
            raise ValueError("LLM did not return a ParsedQuery instance")

        # Normalize stat names and team names
        parsed_result.statistics = normalize_stat_names(parsed_result.statistics)
        parsed_result.teams = normalize_team_names(parsed_result.teams)

        # Store parsed query in state
        state.parsed_query = parsed_result

        # If clarification is needed, set error to signal workflow
        if parsed_result.needs_clarification:
            state.error = ErrorStates.CLARIFICATION_NEEDED
            state.generated_response = (
                parsed_result.clarification_question
                or "I need more information to answer your question. Could you please clarify?"
            )

        return state

    except Exception as e:
        # Handle parsing errors
        # log_error(e, context={"user_query": state.user_query[:100]}, level="warning")

        raise ChatbotError(
            error_type=ErrorStates.PARSING_ERROR,
            message=f"Failed to parse query: {str(e)}",
            details={"user_query": state.user_query[:200]},
            recoverable=True,
        ) from e
