import asyncio

import pandas as pd

from sportsagent.config import setup_logging
from sportsagent.constants import CURRENT_SEASON
from sportsagent.datasource.nflreadpy import NFLReadPyDataSource
from sportsagent.models.chatboterror import ChatbotError, ErrorStates
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.parsedquery import PlayerStatsQuery, QueryFilters, TeamStatsQuery
from sportsagent.models.retrieveddata import RetrievedData

logger = setup_logging(__name__)


NFL_DATASOURCE = NFLReadPyDataSource()


async def retrieve_data(state: ChatbotState) -> ChatbotState:
    try:
        if not state.parsed_query:
            state.error = ErrorStates.PARSING_ERROR
            state.generated_response = "No parsed query available for data retrieval."
            return state
        pq = state.parsed_query

        # Skip retrieval if clarification is needed
        if pq.needs_clarification:
            return state

        if state.pending_action == "enrich":
            if state.retrieved_data is None:
                state.retrieved_data = RetrievedData()

            seasons = [CURRENT_SEASON]
            if pq.player_stats_query and pq.player_stats_query.tp.seasons:
                seasons = pq.player_stats_query.tp.seasons
            elif pq.team_stats_query and pq.team_stats_query.tp.seasons:
                seasons = pq.team_stats_query.tp.seasons

            if not pq.enrichment_datasets:
                raise ChatbotError(
                    error_type=ErrorStates.PARSING_ERROR,
                    message="No enrichment datasets specified.",
                    details={"workflow_intent": pq.workflow_intent},
                    recoverable=True,
                )

            for dataset in pq.enrichment_datasets:
                if dataset == "rosters":
                    df = NFL_DATASOURCE.get_rosters(seasons=seasons)
                elif dataset == "snap_counts":
                    df = NFL_DATASOURCE.get_snap_counts(seasons=seasons)
                else:
                    continue

                records = df.to_dict(orient="records")
                state.retrieved_data.set_dataset(
                    dataset,
                    [{str(k): v for k, v in record.items()} for record in records],
                )

            logger.info(f"Successfully enriched data. Keys: {state.retrieved_data.keys()}")
            return state

        retrieved_data = RetrievedData()

        if psq := pq.player_stats_query:
            player_data = fetch_player_statistics(psq)
            if player_data is not None:
                records = player_data.to_dict(orient="records")
                retrieved_data.add_player_data(
                    [{str(k): v for k, v in record.items()} for record in records],
                )

        if tsq := pq.team_stats_query:
            team_data = fetch_team_statistics(tsq)
            if team_data is not None:
                records = team_data.to_dict(orient="records")
                retrieved_data.add_team_data(
                    [{str(k): v for k, v in record.items()} for record in records],
                )

        if not retrieved_data.players and not retrieved_data.teams:
            raise ChatbotError(
                error_type=ErrorStates.NO_DATA_FOUND,
                message="No statistics found for the requested player(s), position(s), or team(s)",
                details={
                    "players": psq.players if psq else None,
                    "positions": psq.position if psq else None,
                    "teams": tsq.teams if tsq else None,
                    "season": psq.tp.seasons if psq else None,
                },
                recoverable=True,
            )

        state.retrieved_data = retrieved_data
        logger.info(f"Successfully retrieved data. Keys: {state.retrieved_data.keys()}")
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


def fetch_player_statistics(psq: PlayerStatsQuery) -> pd.DataFrame | None:
    try:
        player_data = NFL_DATASOURCE.get_player_stats(
            players=psq.players,
            position=psq.position,
            seasons=psq.tp.seasons,
            summary_level=psq.tp.summary_level,
            stats=psq.stats_cols,
        )

        # if psq.time_period.specific_weeks:
        #     specific_weeks = psq.time_period.specific_weeks
        #     player_data = player_data[
        #         player_data["week"].isin(specific_weeks)
        #     ].copy()

        # Normalize data format
        player_data = normalize_data_format(player_data)

        # # Apply filters
        # if pq.filters:
        #     player_data = apply_filters(player_data, pq.filters)

        return player_data
    except Exception as e:
        logger.error(f"Failed to retrieve data for {psq.queryName}: {e}")
        return None


def fetch_team_statistics(tsq: TeamStatsQuery) -> pd.DataFrame | None:
    try:
        team_data = NFL_DATASOURCE.get_team_stats(
            teams=tsq.teams,
            seasons=tsq.tp.seasons,
            stats=tsq.stats_cols,
            summary_level=tsq.tp.summary_level,
        )

        team_data = normalize_data_format(team_data)
        return team_data
    except Exception as e:
        logger.error(f"Failed to retrieve data for team {tsq.queryName}: {e}")
        return None


def retrieve_data_sync(state: ChatbotState) -> ChatbotState:
    try:
        return asyncio.run(retrieve_data(state))
    except RuntimeError:
        # Fallback for when we are already in an event loop (e.g. nested execution)
        # Note: This might happen in some test environments or if called from async code
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(retrieve_data(state))



def retriever_node(state: ChatbotState) -> ChatbotState:
    logger.info(
        f"Fetching statistics based on query intent: {state.parsed_query.query_intent if state.parsed_query else 'unknown'}"
    )
    try:
        state = retrieve_data_sync(state)

        if state.retrieved_data is not None and len(state.retrieved_data) > 0:
            logger.info(f"Retrieved {len(state.retrieved_data)} datasets")
        else:
            logger.warning("No data retrieved")
            if state.parsed_query:
                state.error = ErrorStates.NO_DATA_FOUND
                state.generated_response = "No statistics found for the requested player(s)."
    except ChatbotError as e:
        logger.error(f"Chatbot error in retriever node: {e.message}")
        state.error = e.error_type
        state.generated_response = e.message
    except Exception as e:
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
        df: DataFrame from nflreadpy datasource

    Returns:
        Normalized DataFrame
    """
    result = df.copy()

    # Ensure numeric columns are proper type
    numeric_columns = [
        "passing_yards",
        "passing_tds",
        "completions",
        "attempts",
        "interceptions",
        "rushing_yards",
        "rushing_tds",
        "rushing_attempts",
        "receiving_yards",
        "receiving_tds",
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

    # Exclude grouping columns and non-aggregatable columns
    exclude_cols = ["season", "week", "year"]
    agg_cols = [col for col in numeric_cols if col not in group_by and col not in exclude_cols]

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
