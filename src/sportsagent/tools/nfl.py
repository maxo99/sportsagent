# import logging
# import re

# import nflreadpy as nfl
# import pandas as pd
# from langchain.tools import tool

# from sportsagent.config import setup_logging
# from sportsagent.constants import CURRENT_SEASON, POSITION_STATS_MAP
# from sportsagent.datasource.nflreadpy import NFLReadPyDataSource, normalize_player_name

# logger = setup_logging(__name__)


# @tool(parse_docstring=True, error_on_invalid_docstring=False)
# def get_player_news(
#     player_name: str,
#     num_articles: int = 5,
# ) -> list[dict]:
#     """Retrieve news articles related to the specified NFL player."""
#     return [{player_name: "No News"}]



# def _get_player_stats(
#     player_name: str,
#     season: int | None = None,
#     week: int | None = None,
#     stats: list[str] | None = None,
# ) -> pd.DataFrame:
#     """
#     Internal function to retrieve player statistics from nflreadpy.

#     Args:
#         player_name: Name of the player
#         season: NFL season year (defaults to current season)
#         week: Specific week number (optional)
#         stats: List of specific statistics to retrieve (optional)
#     """
#     try:
#         logger.info(f"Retrieving stats for {player_name=}, {season=}, {week=}, {stats=}")
#         # Normalize player name
#         normalized_name = normalize_player_name(player_name)

#         if season is None:
#             season = CURRENT_SEASON

#         df = nfl.load_player_stats(seasons=season).to_pandas()

#         # Filter by player name (use player_display_name which has full names)
#         if "player_display_name" in df.columns:
#             result = df[df["player_display_name"].str.strip() == normalized_name].copy()
#         elif "player_name" in df.columns:
#             result = df[df["player_name"].str.strip() == normalized_name].copy()
#         else:
#             raise ValueError("Unable to find player name column in nflreadpy data")

#         if result.empty:
#             raise ValueError(
#                 f"Player '{player_name}' not found in nflreadpy data for season {season}"
#             )

#         # Filter by week if specified
#         if week is not None and "week" in result.columns:
#             result = result[result["week"] == week]

#         if not result.empty and "position" in result.columns:
#             result = _filter_cols_for_position(result)

#         # Filter by requested stats if specified
#         if stats is not None and not result.empty:
#             key_columns = ["player_name", "team", "position", "season", "week"]
#             available_key_cols = [col for col in key_columns if col in result.columns]
#             available_stats = [col for col in stats if col in result.columns]
#             columns_to_select = list(set(available_key_cols + available_stats))
#             result = result[columns_to_select]

#         logger.info(f"Retrieved stats: {result}")

#         return result

#     except ValueError as e:
#         logger.error(f"Validation error: {e}")
#         raise
#     except ConnectionError as e:
#         logger.error(f"Connection error: {e}")
#         raise
#     except Exception as e:
#         logger.error(f"Error retrieving player stats from nflreadpy: {e}")
#         raise Exception(f"Failed to retrieve player stats: {str(e)}") from e



# @tool(parse_docstring=True, error_on_invalid_docstring=False)
# def get_player_stats(
#     player_name: str,
#     season: int | None = None,
#     week: int | None = None,
#     stats: list[str] | None = None,
# ) -> pd.DataFrame:
#     """
#     Retrieve player statistics from nflreadpy.

#     Args:
#         player_name: Name of the player
#         season: NFL season year (defaults to current season)
#         week: Specific week number (optional)
#         stats: List of specific statistics to retrieve (optional)

#     Returns:
#         DataFrame containing the requested player statistics

#     Raises:
#         ValueError: If player not found
#         ConnectionError: If nflreadpy is unavailable
#         Exception: For data retrieval errors
#     """
#     return _get_player_stats(
#         player_name=player_name,
#         season=season,
#         week=week,
#         stats=stats,
#     )
