import asyncio

import pandas as pd

from sportsagent.config import setup_logging
from sportsagent.constants import CURRENT_SEASON
from sportsagent.datasource.nflreadpy import NFLReadPyDataSource
from sportsagent.models.chatboterror import ChatbotError, ErrorStates
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.parsedquery import ChartSpec, PlayerStatsQuery, QueryFilters, TeamStatsQuery
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

        # 1. Base Retrieval
        if state.pending_action in ["retrieve", "rechart"] or state.retrieved_data is None:
            if state.retrieved_data is None or pq.retrieval_merge_intent.mode == "replace":
                retrieved_data = RetrievedData()
            else:
                retrieved_data = state.retrieved_data

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

            state.retrieved_data = retrieved_data

        # 2. Enrichment Retrieval
        if pq.enrichment_datasets:
            if state.retrieved_data is None:
                state.retrieved_data = RetrievedData()

            seasons = [CURRENT_SEASON]
            if pq.player_stats_query and pq.player_stats_query.tp.seasons:
                seasons = pq.player_stats_query.tp.seasons
            elif pq.team_stats_query and pq.team_stats_query.tp.seasons:
                seasons = pq.team_stats_query.tp.seasons

            for dataset in pq.enrichment_datasets:
                if dataset == "rosters":
                    df = NFL_DATASOURCE.get_rosters(seasons=seasons)
                elif dataset == "snap_counts":
                    df = NFL_DATASOURCE.get_snap_counts(seasons=seasons)
                elif dataset == "player_info":
                    df = NFL_DATASOURCE.get_player_data()
                else:
                    continue

                records = df.to_dict(orient="records")
                state.retrieved_data.set_dataset(
                    dataset,
                    [{str(k): v for k, v in record.items()} for record in records],
                )

            # Optional automatic merging if join keys are provided
            if pq.enrichment_options.join_keys and state.retrieved_data:
                _perform_automatic_merges(state)

            logger.info(f"Successfully enriched data. Keys: {state.retrieved_data.keys()}")

        # 3. Final Validation
        if state.retrieved_data is None or len(state.retrieved_data) == 0:
            raise ChatbotError(
                error_type=ErrorStates.NO_DATA_FOUND,
                message="No statistics found for the requested player(s), position(s), or team(s)",
                details={
                    "players": pq.player_stats_query.players if pq.player_stats_query else None,
                    "teams": pq.team_stats_query.teams if pq.team_stats_query else None,
                    "season": pq.player_stats_query.tp.seasons if pq.player_stats_query else None,
                },
                recoverable=True,
            )

        logger.info(f"Successfully retrieved/enriched data. Keys: {state.retrieved_data.keys()}")
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
    except RuntimeError as exc:
        if "already running" not in str(exc).lower():
            raise
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(retrieve_data(state))
        finally:
            loop.close()


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
    chart_spec: ChartSpec | None = None,
) -> pd.DataFrame:
    """
    Aggregate data based on chart specification.

    Args:
        df: DataFrame with statistics
        chart_spec: Chart specifications including aggregation and grouping

    Returns:
        Aggregated DataFrame
    """
    if chart_spec is None or chart_spec.aggregation is None or df.empty:
        return df

    # Default grouping by x_axis if not specified
    group_by = [chart_spec.x_axis]
    if chart_spec.group_by:
        group_by.append(chart_spec.group_by)

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
        "mean": "mean",
        "max": "max",
        "min": "min",
        "count": "count",
    }

    agg_func = agg_func_map.get(chart_spec.aggregation.lower(), "sum")

    try:
        result = df.groupby(group_by)[agg_cols].agg(agg_func).reset_index()
        return result
    except Exception as e:
        logger.warning(f"Aggregation failed: {e}. Returning original data.")
        return df


def _perform_automatic_merges(state: ChatbotState) -> None:
    """
    Helper to merge enrichment data into primary datasets based on join keys.
    """
    pq = state.parsed_query
    if not pq.enrichment_options.join_keys or not state.retrieved_data:
        return

    # For each enrichment dataset requested
    for dataset_key in pq.enrichment_datasets:
        extra_data = state.retrieved_data.extra.get(dataset_key)
        if not extra_data:
            continue

        extra_df = pd.DataFrame(extra_data)

        # Try to merge into players if applicable
        if state.retrieved_data.players:
            players_df = pd.DataFrame(state.retrieved_data.players)
            merged = _attempt_merge(players_df, extra_df, pq.enrichment_options.join_keys)
            if merged is not None:
                logger.info(f"Successfully merged {dataset_key} into players")
                state.retrieved_data.players = [
                    {str(k): v for k, v in record.items()}
                    for record in merged.to_dict(orient="records")
                ]

        # Try to merge into teams if applicable
        if state.retrieved_data.teams:
            teams_df = pd.DataFrame(state.retrieved_data.teams)
            merged = _attempt_merge(teams_df, extra_df, pq.enrichment_options.join_keys)
            if merged is not None:
                logger.info(f"Successfully merged {dataset_key} into teams")
                state.retrieved_data.teams = [
                    {str(k): v for k, v in record.items()}
                    for record in merged.to_dict(orient="records")
                ]


def _attempt_merge(
    primary_df: pd.DataFrame, extra_df: pd.DataFrame, join_keys: list[str]
) -> pd.DataFrame | None:
    """
    Attempts to merge extra_df into primary_df using provided join_keys.
    Handles potentially different column names in join_keys (if colon separated).
    """
    for key_pair in join_keys:
        if ":" in key_pair:
            left_key, right_key = key_pair.split(":", 1)
        else:
            left_key, right_key = key_pair, key_pair

        if left_key in primary_df.columns and right_key in extra_df.columns:
            try:
                # Use left join to preserve all primary records
                return primary_df.merge(extra_df, left_on=left_key, right_on=right_key, how="left")
            except Exception as e:
                logger.warning(f"Merge failed on {left_key}/{right_key}: {e}")
    return None
