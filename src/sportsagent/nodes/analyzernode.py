import pandas as pd

from sportsagent import utils
from sportsagent.agents.analyzeragent import AnalyzerAgent
from sportsagent.config import settings, setup_logging
from sportsagent.models.chatboterror import UNKNOWN_ERROR_RESPONSE, ErrorStates
from sportsagent.models.chatbotstate import ChatbotState

logger = setup_logging(__name__)


def analyzer_node(state: ChatbotState) -> ChatbotState:
    logger.info("Generating insights using AnalyzerAgent")
    analyzer_agent = None
    try:
        if state.error:
            logger.info("Analyzer Node exiting due to prior error")
            return state

        if not state.retrieved_data:
            logger.error("Analyzer Node exiting due to no retrieved data")
            state.generated_response = "No data available for analysis."
            return state

        # Initialize and run the Analyzer Agent
        analyzer_agent = AnalyzerAgent()
        df = pd.DataFrame(state.retrieved_data)

        # Prepare instructions with data context
        user_instructions = utils.get_prompt_template("analyzer_instructions.j2").render(
            data_sample=df.head(3).to_string(),
            row_count=len(df),
            user_instructions=state.user_query,
        )

        analyzer_agent.invoke_agent(
            user_instructions=user_instructions,
            data_raw=df,
            session_id=state.session_id,
        )

        # Capture execution trace
        state.internal_trace = analyzer_agent.get_execution_trace(settings.SHOW_INTERNAL)

        # Check for tool calls or fallback request string
        tool_calls = analyzer_agent.get_tool_calls()
        ai_message = analyzer_agent.get_ai_message(markdown=False)

        request_triggered = (
            tool_calls and tool_calls[-1] == "request_more_data"
        ) or "REQUEST_MORE_DATA:" in str(ai_message)

        if request_triggered:
            new_query = _extract_data_request_query(analyzer_agent, ai_message)

            if new_query:
                logger.info(f"Agent requested more data: {new_query}")
                state.user_query = new_query
                state.generated_response = f"__ROUTE_TO_RETRIEVER__: {new_query}"
                return state

            logger.warning("Could not find REQUEST_MORE_DATA string despite trigger")

        # Process standard response
        state.generated_response = ai_message

        if any(k in ai_message.lower() for k in ["visualiz", "plot", "chart"]):
            state.needs_visualization = True

        logger.info(f"Generated response ({len(state.generated_response)} chars)")

    except Exception as e:
        logger.error(f"Analyzer Node error: {e}", exc_info=True)

        # Attempt to capture trace from partial execution
        if analyzer_agent is not None:
            try:
                state.internal_trace = analyzer_agent.get_execution_trace(show_ai=True)
                logger.error(f"Internal trace captured with {len(state.internal_trace)} entries")
            except Exception:
                logger.warning("Failed to retrieve partial trace from analyzer agent")

        state.error = ErrorStates.RESPONSE_GENERATION_ERROR
        state.generated_response = UNKNOWN_ERROR_RESPONSE

    return state


def _extract_data_request_query(agent: AnalyzerAgent, ai_message: str) -> str | None:
    """Helper to extract the query from a data request."""

    def extract(text):
        if "REQUEST_MORE_DATA:" in text:
            try:
                return text.split("REQUEST_MORE_DATA:", 1)[1].strip()
            except IndexError:
                return None
        return None

    # 1. Check AI message first
    if query := extract(ai_message):
        return query

    # 2. Check internal messages backwards
    internal_messages = agent.get_internal_messages() or []
    for msg in reversed(internal_messages):
        if hasattr(msg, "content") and (query := extract(str(msg.content))):
            return query

    return None
