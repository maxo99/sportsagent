import glob
import re
from urllib.request import urlretrieve

import nflreadpy as nfl
import pandas as pd

from sportsagent.config import setup_logging
from sportsagent.constants import CURRENT_SEASON, POSITION_STATS_MAP, STAT_MAPPINGS, TEAM_MAPPINGS

logger = setup_logging(__name__)


class NFLReadPyDataSource:
    TEAM_COLORS: dict[str, list[str]]
    TEAM_LOGO_PATHS: dict[str, str]
    logos_preloaded = False

    def __init__(self) -> None:
        # # from nflreadpy.config import update_config

        # # update_config(
        # #     cache_mode="memory",
        # #     cache_dir='~/.nflreadpy',
        # #     cache_duration=86400,
        # #     verbose=False,
        # #     timeout=30,
        # #     user_agent='nflreadpy/v0.1.1'
        # # )
        self.TEAM_COLORS = {}
        self.TEAM_LOGO_PATHS = {}
        self.preload_teams_data()
        super().__init__()

    @property
    def name(self) -> str:
        return "datasource_nflreadpy"

    def get_player_stats(
        self,
        player_name: str,
        season: int | None = None,
        week: int | None = None,
        stats: list[str] | None = None,
    ) -> pd.DataFrame:
        try:
            logger.info(f"Retrieving stats for {player_name=}, {season=}, {week=}, {stats=}")
            # Normalize player name
            normalized_name = normalize_player_name(player_name)

            if season is None:
                season = CURRENT_SEASON

            df = nfl.load_player_stats(seasons=season).to_pandas()

            # Filter by player name (use player_display_name which has full names)
            if "player_display_name" in df.columns:
                result = df[df["player_display_name"].str.strip() == normalized_name].copy()
            elif "player_name" in df.columns:
                result = df[df["player_name"].str.strip() == normalized_name].copy()
            else:
                raise ValueError("Unable to find player name column in nflreadpy data")

            if result.empty:
                logger.error(
                    f"Player '{player_name}' not found in nflreadpy data for season {season}"
                )
                raise ValueError(
                    f"Player '{player_name}' not found in nflreadpy data for season {season}"
                )

            # Filter by week if specified
            if week is not None and "week" in result.columns:
                result = result[result["week"] == week]

            if not result.empty and "position" in result.columns:
                result = _filter_cols_for_position(result)

            # Filter by requested stats if specified
            if stats is not None and not result.empty:
                key_columns = ["player_name", "team", "position", "season", "week"]
                available_key_cols = [col for col in key_columns if col in result.columns]
                available_stats = [col for col in stats if col in result.columns]
                columns_to_select = list(set(available_key_cols + available_stats))
                result = result[columns_to_select]

            logger.info(
                f"Retrieved dataframe with rows: {len(result)} cols: {list(result.columns)}"
            )
            return result

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving player stats from nflreadpy: {e}")
            raise Exception(f"Failed to retrieve player stats: {str(e)}") from e

    def get_position_stats(
        self,
        position: str,
        season: int | None = None,
        week: int | None = None,
        stats: list[str] | None = None,
    ) -> pd.DataFrame:
        try:
            logger.info(f"Retrieving stats for {position=}, {season=}, {week=}, {stats=}")

            if season is None:
                season = CURRENT_SEASON

            df = nfl.load_player_stats(seasons=season).to_pandas()

            if "position" in df.columns:
                result = df[df["position"].str.strip() == position.upper()].copy()
            else:
                raise ValueError("Unable to find position column in nflreadpy data")

            if result.empty:
                raise ValueError(f"'{position=}' not found in nflreadpy data for {season=}")

            # Filter by week if specified
            if week is not None and "week" in result.columns:
                result = result[result["week"] == week]

            if not result.empty and "position" in result.columns:
                result = _filter_cols_for_position(result)

            # Filter by requested stats if specified
            if stats is not None and not result.empty:
                key_columns = ["player_name", "team", "position", "season", "week"]
                available_key_cols = [col for col in key_columns if col in result.columns]
                available_stats = [col for col in stats if col in result.columns]
                columns_to_select = list(set(available_key_cols + available_stats))
                result = result[columns_to_select]

            logger.info(f"Retrieved dataframe shape {result.shape} cols: {list(result.columns)}")
            return result

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving position stats from nflreadpy: {e}")
            raise Exception(f"Failed to retrieve position stats: {str(e)}") from e

    def preload_teams_data(self) -> None:
        try:
            logger.info("Preloading teams data from nflreadpy")
            teams = nfl.load_teams().to_pandas()

            # If no .tif files exist in logos set logos_preloaded = True
            logo_files = glob.glob("data/logos/*.tif")
            if len(logo_files) >= len(teams):
                self.logos_preloaded = True

            for _, row in teams.iterrows():
                team_abbr = row["team_abbr"]
                colors = []
                if pd.notna(row.get("team_color")):
                    colors.append(row["team_color"])
                if pd.notna(row.get("team_color2")):
                    colors.append(row["team_color2"])
                self.TEAM_COLORS[team_abbr] = colors

                if not self.logos_preloaded:
                    urlretrieve(row["team_logo_espn"], f"data/logos/{row['team_abbr']}.tif")
                    self.TEAM_LOGO_PATHS[team_abbr] = f"data/logos/{row['team_abbr']}.tif"
            self.logos_preloaded = True
            logger.info("Teams data preloaded successfully")
        except Exception as e:
            logger.error(f"Error preloading teams data: {e}")


def _filter_cols_for_position(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter DataFrame columns based on player position.

    Args:
        df: DataFrame containing player stats

    Returns:
        Filtered DataFrame with relevant columns for the specified position
    """
    return df[POSITION_STATS_MAP.get(df.iloc[0]["position"].upper(), [])]


def normalize_player_name(
    name: str,
    strict: bool = False,
) -> str:
    if not name or not isinstance(name, str):
        if strict:
            raise Exception(f"Invalid player name: {name}")
        return ""

    # Strip whitespace and convert to lowercase for lookup
    name_clean = name.strip().lower()

    # Apply standard normalization
    # Remove extra whitespace
    normalized = re.sub(r"\s+", " ", name_clean)

    # Handle common punctuation patterns
    # Convert "AJ" to "A.J.", "DJ" to "D.J.", etc.
    normalized = re.sub(r"\b([a-z])([a-z])\b", r"\1.\2.", normalized)

    # Convert to Title Case
    normalized = normalized.title()

    # Handle special cases like "McCaffrey", "O'Brien"
    normalized = re.sub(r"Mc([a-z])", lambda m: f"Mc{m.group(1).upper()}", normalized)
    normalized = re.sub(r"O'([a-z])", lambda m: f"O'{m.group(1).upper()}", normalized)

    return normalized


def normalize_stat_names(stats: list[str]) -> list[str]:
    normalized = []
    for stat in stats:
        stat_lower = stat.lower().strip()
        normalized_stat = STAT_MAPPINGS.get(stat_lower, stat_lower.replace(" ", "_"))
        normalized.append(normalized_stat)
    return normalized


def normalize_team_names(teams: list[str]) -> list[str]:
    normalized = []
    for team in teams:
        team_lower = team.lower().strip()
        normalized_team = TEAM_MAPPINGS.get(team_lower, team)
        normalized.append(normalized_team)
    return normalized
