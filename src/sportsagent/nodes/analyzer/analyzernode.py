import pandas as pd

from sportsagent.config import settings, setup_logging
from sportsagent.models.chatboterror import UNKNOWN_ERROR_RESPONSE, ErrorStates
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.nodes.analyzer import get_analyzer_template
from sportsagent.nodes.analyzer.analyzeragent import AnalyzerAgent

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

        analyzer_agent = AnalyzerAgent()

        data_context = {}
        data_sample_str = ""
        total_rows = 0

        for key, records in state.retrieved_data.items():
            if records:
                df = pd.DataFrame(records)
                data_context[key] = df
                data_sample_str += f"\n### Dataset: {key}\n{df.head(3).to_string()}\n"
                total_rows += len(df)

        primary_df = pd.DataFrame()
        if "players" in data_context:
            primary_df = data_context["players"]
        elif "teams" in data_context:
            primary_df = data_context["teams"]
        elif data_context:
            primary_df = list(data_context.values())[0]

        # Prepare instructions with data context
        user_instructions = get_analyzer_template("analyzer_instructions.j2").render(
            data_sample=data_sample_str,
            row_count=total_rows,
            user_instructions=state.user_query,
        )

        analyzer_agent.invoke_agent(
            user_instructions=user_instructions,
            data_raw=primary_df,
            session_id=state.session_id,
        )

        state.internal_trace = analyzer_agent.get_execution_trace(settings.SHOW_INTERNAL)

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
                state.pending_action = "retrieve"
                state.approval_required = True
                state.approval_result = None
                state.generated_response = ""
                return state

            logger.warning("Could not find REQUEST_MORE_DATA string despite trigger")

        state.generated_response = ai_message

        state.approval_required = False

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
