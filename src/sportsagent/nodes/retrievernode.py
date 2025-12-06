import asyncio

import pandas as pd

from sportsagent.config import setup_logging
from sportsagent.datasource.nflreadpy import NFLReadPyDataSource
from sportsagent.models.chatboterror import ChatbotError, ErrorStates
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.parsedquery import QueryFilters

logger = setup_logging(__name__)


async def retrieve_data(state: ChatbotState) -> ChatbotState:
    try:
        if not state.parsed_query:
            state.error = ErrorStates.PARSING_ERROR
            state.generated_response = "No parsed query available for data retrieval."
            return state

        # Skip retrieval if clarification is needed
        if state.parsed_query.needs_clarification:
            return state

        # Extract query parameters
        players = state.parsed_query.players
        statistics = state.parsed_query.statistics
        time_period = state.parsed_query.time_period
        filters = state.parsed_query.filters
        aggregation = state.parsed_query.aggregation

        if not players:
            raise ChatbotError(
                error_type=ErrorStates.VALIDATION_ERROR,
                message="No players specified in query",
                details={"parsed_query": state.parsed_query},
                recoverable=True,
            )

        # Initialize router
        datasource = NFLReadPyDataSource()

        # Retrieve data for each player
        all_data: list[pd.DataFrame] = []

        for player in players:
            try:
                # Extract time period parameters
                season = time_period.season
                week = time_period.week
                if week is None:
                    specific_weeks = time_period.specific_weeks
                    if specific_weeks:
                        week = specific_weeks[0]

                # Retrieve data with fallback
                player_data = datasource.get_player_stats(
                    player_name=player,
                    season=season,
                    week=week,
                    stats=statistics if statistics else None,
                )

                # Normalize data format
                player_data = normalize_data_format(player_data)

                # Apply filters
                if filters:
                    player_data = apply_filters(player_data, filters)

                all_data.append(player_data)

            except Exception as e:
                logger.error(f"Failed to retrieve data for {player}: {e}")
                # Continue with other players
                continue

        if not all_data:
            raise ChatbotError(
                error_type=ErrorStates.NO_DATA_FOUND,
                message="No statistics found for the requested player(s)",
                details={
                    "players": players,
                    "season": time_period.season,
                    "week": time_period.week,
                },
                recoverable=True,
            )

        # Combine all player data
        combined_data = pd.concat(all_data, ignore_index=True)

        # Apply aggregation if requested
        if aggregation:
            combined_data = aggregate_data(
                combined_data, aggregation, group_by=["player_name", "team", "position"]
            )

        # Store retrieved data in state
        state.retrieved_data = combined_data

        logger.info(
            f"Successfully retrieved {len(combined_data)} records for {len(players)} player(s)"
        )

        return state

    except ChatbotError:
        # Re-raise ChatbotError to be handled by workflow
        raise
    except Exception as e:
        # Wrap unexpected errors in ChatbotError
        raise ChatbotError(
            error_type=ErrorStates.RETRIEVAL_ERROR,
            message=f"Error retrieving data: {str(e)}",
            details={"parsed_query": state.parsed_query, "error": str(e)},
            recoverable=True,
        ) from e


def retrieve_data_sync(state: ChatbotState) -> ChatbotState:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(retrieve_data(state))


def retriever_node(state: ChatbotState) -> ChatbotState:
    logger.info("Fetching player statistics")
    try:
        state = retrieve_data_sync(state)

        if state.retrieved_data is not None and not state.retrieved_data.empty:
            logger.info(f"Retrieved {len(state.retrieved_data)} records")
        else:
            logger.warning("No data retrieved")
            if state.parsed_query:
                # Create helpful error response
                # context = {
                #     "players": state.parsed_query.players,
                #     "season": state.parsed_query.time_period.season,
                # }
                # error_response = create_error_response(ErrorStates.NO_DATA_FOUND, details=context)
                # state.error = error_response["error"]
                # state.generated_response = error_response["generated_response"]
                state.error = ErrorStates.NO_DATA_FOUND
                state.generated_response = "No statistics found for the requested player(s)."

    # except ChatbotError as e:
    #     # Handle known chatbot errors
    #     error_info = handle_error(
    #         e, context={"node": "retriever", "parsed_query": state.get("parsed_query", {})}
    #     )
    #     state.error = error_info["error_type"]
    #     state.generated_response = error_info["user_message"]
    except Exception as e:
        # Handle unexpected errors
        # error_info = handle_error(
        #     e,
        #     context={"node": "retriever", "parsed_query": state.parsed_query},
        #     default_error_type=ErrorStates.RETRIEVAL_ERROR,
        # )
        # state.error = error_info["error_type"]
        # state.generated_response = error_info["user_message"]
        logger.error(f"Unexpected error in retriever node: {e}")
        state.error = ErrorStates.RETRIEVAL_ERROR
        state.generated_response = "An unexpected error occurred while retrieving data."
    return state


def apply_filters(df: pd.DataFrame, filters: QueryFilters) -> pd.DataFrame:
    result = df.copy()

    # Apply opponent filter
    if filters.opponent:
        opponent = filters.opponent
        if "opponent" in result.columns:
            result = result[result["opponent"].str.contains(opponent, case=False, na=False)]

    # Apply home/away filter
    if filters.home_away:
        home_away = filters.home_away.lower()
        if "home_away" in result.columns:
            result = result[result["home_away"].str.lower() == home_away]

    # Apply min value filter
    if filters.min_value is not None:
        min_val = filters.min_value
        # Apply to numeric columns
        numeric_cols = result.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            if col not in ["season", "week", "games_played"]:
                result = result[result[col] >= min_val]

    # Apply max value filter
    if filters.max_value is not None:
        max_val = filters.max_value
        # Apply to numeric columns
        numeric_cols = result.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            if col not in ["season", "week", "games_played"]:
                result = result[result[col] <= max_val]

    return result


def normalize_data_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize data formats across different sources.

    Ensures consistent column names, data types, and structure
    regardless of which data source provided the data.

    Args:
        df: DataFrame from any data source

    Returns:
        Normalized DataFrame
    """
    result = df.copy()

    # Standardize column names
    column_mapping = {
        "player": "player_name",
        "year": "season",
        "tm": "team",
        "pos": "position",
        "pass_yds": "passing_yards",
        "pass_td": "passing_touchdowns",
        "rush_yds": "rushing_yards",
        "rush_td": "rushing_touchdowns",
        "rec_yds": "receiving_yards",
        "rec_td": "receiving_touchdowns",
        "rec": "receptions",
        "tgt": "targets",
        "att": "attempts",
        "cmp": "completions",
        "int": "interceptions",
    }

    result = result.rename(columns=column_mapping)

    # Ensure numeric columns are proper type
    numeric_columns = [
        "passing_yards",
        "passing_touchdowns",
        "completions",
        "attempts",
        "interceptions",
        "rushing_yards",
        "rushing_touchdowns",
        "rushing_attempts",
        "receiving_yards",
        "receiving_touchdowns",
        "receptions",
        "targets",
        "season",
        "week",
        "games_played",
    ]

    for col in numeric_columns:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")

    # Fill NaN values with 0 for statistics
    stat_columns = [col for col in numeric_columns if col not in ["season", "week"]]
    for col in stat_columns:
        if col in result.columns:
            result[col] = result[col].fillna(0)

    return result


def aggregate_data(
    df: pd.DataFrame,
    aggregation: str | None = None,
    group_by: list[str] | None = None,
) -> pd.DataFrame:
    """
    Aggregate data based on query requirements.

    Args:
        df: DataFrame with player statistics
        aggregation: Type of aggregation ('sum', 'average', 'max', 'min')
        group_by: Columns to group by before aggregation

    Returns:
        Aggregated DataFrame
    """
    if aggregation is None or df.empty:
        return df

    # Default grouping by player if not specified
    if group_by is None:
        group_by = ["player_name"]

    # Ensure group_by columns exist
    group_by = [col for col in group_by if col in df.columns]
    if not group_by:
        return df

    # Select numeric columns for aggregation
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    # Exclude grouping columns
    agg_cols = [col for col in numeric_cols if col not in group_by]

    if not agg_cols:
        return df

    # Perform aggregation
    agg_func_map = {
        "sum": "sum",
        "average": "mean",
        "avg": "mean",
        "mean": "mean",
        "max": "max",
        "maximum": "max",
        "min": "min",
        "minimum": "min",
    }

    agg_func = agg_func_map.get(aggregation.lower(), "sum")

    try:
        result = df.groupby(group_by)[agg_cols].agg(agg_func).reset_index()
        return result
    except Exception as e:
        logger.warning(f"Aggregation failed: {e}. Returning original data.")
        return df
