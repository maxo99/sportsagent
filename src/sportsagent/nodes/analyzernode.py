import asyncio

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai.chat_models import ChatOpenAI
from pandas import DataFrame

from sportsagent import utils
from sportsagent.config import setup_logging
from sportsagent.constants import CURRENT_YEAR
from sportsagent.models.chatboterror import ChatbotError, ErrorStates
from sportsagent.models.chatbotstate import ChatbotState, ConversationHistory
from sportsagent.models.comparisonmetric import ComparisionMetrics, ComparisonMetric
from sportsagent.models.parsedquery import ParsedQuery

logger = setup_logging(__name__)


def format_conversation_history(conversation_history: ConversationHistory) -> str:
    if not conversation_history:
        return "No previous conversation."

    # Get last 5 turns for better context on follow-up questions
    recent_turns = (
        conversation_history[-5:] if len(conversation_history) >= 5 else conversation_history
    )

    formatted = []
    for i, turn in enumerate(recent_turns, 1):
        user_query = turn.get("user_query", "")
        bot_response = turn.get("bot_response", "")
        mentioned_players = turn.get("mentioned_players", [])
        mentioned_stats = turn.get("mentioned_stats", [])

        if user_query:
            formatted.append(f"Turn {i} - User: {user_query}")
        if bot_response:
            # Truncate long responses but keep key info
            if len(bot_response) > 300:
                bot_response = bot_response[:300] + "..."
            formatted.append(f"Turn {i} - Assistant: {bot_response}")

        # Add context about what was discussed
        if mentioned_players or mentioned_stats:
            context_parts = []
            if mentioned_players:
                context_parts.append(f"Players: {', '.join(mentioned_players)}")
            if mentioned_stats:
                context_parts.append(f"Stats: {', '.join(mentioned_stats)}")
            formatted.append(f"  [Context: {' | '.join(context_parts)}]")

        formatted.append("")

    return "\n".join(formatted)


def format_dataframe_for_prompt(df: pd.DataFrame) -> str:
    if df.empty:
        return "No data available."

    # Convert DataFrame to a structured format
    formatted_lines = []

    for _, row in df.iterrows():
        player_info = []
        # Basic info
        if "player_name" in row:
            player_info.append(f"Player: {row['player_name']}")
        if "team" in row:
            player_info.append(f"Team: {row['team']}")
        if "position" in row:
            player_info.append(f"Position: {row['position']}")
        if "season" in row:
            player_info.append(f"Season: {int(row['season'])}")
        if "week" in row and pd.notna(row["week"]):
            player_info.append(f"Week: {int(row['week'])}")

        formatted_lines.append(" | ".join(player_info))

        # Statistics
        stat_lines = []
        stat_columns = [
            col
            for col in df.columns
            if col
            not in [
                "player_name",
                "team",
                "position",
                "season",
                "week",
                "games_played",
            ]
        ]

        for col in stat_columns:
            if pd.notna(row[col]) and row[col] != 0:
                # Format the stat name nicely
                stat_name = col.replace("_", " ").title()
                value = row[col]

                # Format based on type
                if isinstance(value, float):
                    if "rate" in col or "percentage" in col:
                        stat_lines.append(f"  {stat_name}: {value:.1f}%")
                    else:
                        stat_lines.append(f"  {stat_name}: {value:.2f}")
                else:
                    stat_lines.append(f"  {stat_name}: {value}")

        if stat_lines:
            formatted_lines.extend(stat_lines)

        formatted_lines.append("")  # Empty line between players

    return "\n".join(formatted_lines)


def calculate_comparison_metrics(df: pd.DataFrame) -> ComparisionMetrics | None:
    if df.empty or len(df) < 2:
        return None

    metrics = ComparisionMetrics(player_count=len(df), comparisons=[])

    # Get numeric columns for comparison
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    stat_cols = [col for col in numeric_cols if col not in ["season", "week", "games_played"]]

    # Calculate differences for each stat
    for stat in stat_cols:
        if stat in df.columns and df[stat].notna().any():
            values = df[stat].dropna()
            if len(values) >= 2:
                max_val = values.max()
                min_val = values.min()
                if max_val > 0:
                    pct_diff = ((max_val - min_val) / max_val) * 100
                    # Find players with max and min values
                    max_players = df.loc[df[stat] == max_val, "player_name"]
                    max_player = (
                        max_players.iloc[0]
                        if isinstance(max_players, pd.Series)
                        and not max_players.empty
                        and "player_name" in df.columns
                        else "Unknown"
                    )
                    min_players = df.loc[df[stat] == min_val, "player_name"]
                    min_player = (
                        min_players.iloc[0]
                        if isinstance(min_players, pd.Series)
                        and not min_players.empty
                        and "player_name" in df.columns
                        else "Unknown"
                    )

                    metrics.comparisons.append(
                        ComparisonMetric(
                            stat=stat,
                            max_value=max_val,
                            min_value=min_val,
                            difference=max_val - min_val,
                            percent_difference=pct_diff,
                            leader=max_player,
                            trailing=min_player,
                        )
                    )

    return metrics


def build_insight_prompt(
    retrieved_data: DataFrame,
    parsed_query: ParsedQuery,
    conversation_history: ConversationHistory,
) -> str:
    # Format the data
    data_str = format_dataframe_for_prompt(retrieved_data)

    # Build the prompt
    prompt = utils.get_prompt_template("insight_generation.j2").render(
        current_year=CURRENT_YEAR,
        data=data_str,
        parsed_query=parsed_query,
    )

    comparison_metrics = None
    if parsed_query.comparison and len(retrieved_data) > 1:
        comparison_metrics = calculate_comparison_metrics(retrieved_data)

        if comparison_metrics and comparison_metrics.comparisons:
            prompt += "\n\nCOMPARISON INSIGHTS:\n"
            for comp in comparison_metrics.comparisons[:5]:  # Top 5 differences
                stat_name = comp.stat.replace("_", " ").title()
                prompt += f"- {stat_name}: {comp.leader} leads with {comp.max_value:.1f} vs {comp.trailing} with {comp.min_value:.1f} "
                prompt += (
                    f"(difference: {comp.difference:.1f}, {comp.percent_difference:.1f}% gap)\n"
                )

    # Add conversation context
    if conversation_history:
        history_str = format_conversation_history(conversation_history)
        prompt += utils.get_prompt_template("conversation_history.j2").render(
            history_str=history_str
        )

    prompt += utils.get_prompt_template("generating_insights_instructions.j2").render()

    return prompt


def _generate_insights_sync(state: ChatbotState) -> ChatbotState:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_generate_insights(state))


async def _generate_insights(state: ChatbotState) -> ChatbotState:
    try:
        # Check for errors from previous nodes
        if state.error and state.error != "":
            # Error already handled, skip LLM generation
            return state
        if state.parsed_query is None:
            raise ChatbotError(
                error_type=ErrorStates.PARSING_ERROR,
                message="Cannot generate insights without a parsed query",
                details={},
                recoverable=False,
            )

        # Validate retrieved data
        if state.retrieved_data is None or state.retrieved_data.empty:
            raise ChatbotError(
                error_type=ErrorStates.RETRIEVAL_ERROR,
                message="No data available for insight generation",
                details={"parsed_query": state.parsed_query},
                recoverable=True,
            )

        # Build the prompt
        system_prompt = build_insight_prompt(
            retrieved_data=state.retrieved_data,
            parsed_query=state.parsed_query,
            conversation_history=state.conversation_history,
        )

        # Initialize OpenAI
        llm = ChatOpenAI(
            model="gpt-4",
        )

        # Create messages
        user_query = state.user_query if state.user_query else "Analyze these statistics"
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User's question: {user_query}"),
        ]

        # Generate insights
        logger.info("Generating insights from LLM...")
        response = llm.invoke(
            messages,
            temperature=0.7,
            max_tokens=800,
        )

        # Extract the generated text
        generated_response = response.content

        if not isinstance(generated_response, str) or generated_response.strip() == "":
            raise ChatbotError(
                error_type=ErrorStates.RESPONSE_GENERATION_ERROR,
                message="LLM returned an empty response",
                details={},
                recoverable=True,
            )
        state.generated_response = generated_response

        logger.info(f"Successfully generated insights ({len(generated_response)} characters)")

        return state

    except ChatbotError:
        # Re-raise ChatbotError to be handled by workflow
        raise
    except Exception as e:
        # Handle LLM API errors
        # log_error(
        #     e,
        #     context={
        #         "operation": "insight_generation",
        #         "data_size": len(retrieved_data) if retrieved_data is not None else 0,
        #     },
        #     level="warning",
        # )

        error_str = str(e).lower()
        if "rate" in error_str and "limit" in error_str:
            error_type = ErrorStates.LLM_RATE_LIMIT
        elif "timeout" in error_str:
            error_type = ErrorStates.LLM_TIMEOUT
        else:
            error_type = ErrorStates.RESPONSE_GENERATION_ERROR

        raise ChatbotError(
            error_type=error_type,
            message=f"Failed to generate insights: {str(e)}",
            details={"error": str(e)},
            recoverable=True,
        ) from e


def analyzer_node(state: ChatbotState) -> ChatbotState:
    logger.info("Generating insights")

    try:
        state = _generate_insights_sync(state)

        if state.generated_response:
            logger.info(f"Generated response ({len(state.generated_response)} chars)")
        else:
            logger.warning("No response generated")
    # except ChatbotError as e:
    #     # Handle known chatbot errors
    #     from error_handler import handle_llm_error

    #     error_response = handle_llm_error(e, operation="insight generation")
    #     state["error"] = error_response["error"]
    #     state["generated_response"] = error_response["generated_response"]
    except Exception as e:
        # Handle unexpected errors (likely LLM API errors)
        # from error_handler import handle_llm_error
        logger.error(f"LLM Node error: {e}", exc_info=True)
        state.error = ErrorStates.RESPONSE_GENERATION_ERROR
        state.generated_response = (
            "I'm sorry, but I'm currently unable to generate insights due to a technical issue. "
            "Please try again later."
        )
        # error_response = handle_llm_error(e, operation="insight generation")
        # state.error = error_response["error"]
        # state.generated_response = error_response["generated_response"]

    return state


# def calculate_league_context(df: pd.DataFrame, stat: str) -> dict[str, any]:
#     """
#     Calculate league context for a statistic (averages, rankings).

#     Note: This is a simplified version. In production, you would query
#     actual league-wide data for accurate context.

#     Args:
#         df: DataFrame with player statistics
#         stat: Statistic to provide context for

#     Returns:
#         dictionary with league context information
#     """
#     context = {}

#     if stat not in df.columns or df[stat].isna().all():
#         return context

#     # Calculate basic statistics
#     values = df[stat].dropna()
#     if len(values) > 0:
#         context['mean'] = values.mean()
#         context['median'] = values.median()
#         context['std'] = values.std()
#         context['min'] = values.min()
#         context['max'] = values.max()

#     # Approximate league averages (these would come from actual data in production)
#     # These are rough 2023 NFL averages for common stats
#     league_averages = {
#         'passing_yards': 250,
#         'passing_touchdowns': 1.5,
#         'completion_rate': 64.0,
#         'interceptions': 0.8,
#         'rushing_yards': 80,
#         'rushing_touchdowns': 0.5,
#         'receiving_yards': 50,
#         'receptions': 4.5,
#         'targets': 6.5,
#         'yards_per_attempt': 7.0,
#         'yards_per_reception': 11.0,
#     }

#     if stat in league_averages:
#         context['league_average'] = league_averages[stat]

#     return context
