from pathlib import Path
from typing import Literal
from urllib.request import urlretrieve

import nflreadpy as nfl
import pandas as pd

from sportsagent.config import Settings, setup_logging
from sportsagent.models.chatboterror import RetrievalError

logger = setup_logging(__name__)


class NFLReadPyDataSource:
    TEAM_COLORS: dict[str, list[str]]
    TEAM_LOGO_PATHS: dict[str, str]
    logos_preloaded = False

    def __init__(self) -> None:
        from nflreadpy.config import update_config

        self.settings = Settings()

        if self.settings.NFLREADPY_CACHE_MODE != "off":
            cache_dir = self.settings.NFLREADPY_CACHE_DIR
            if isinstance(cache_dir, str):
                cache_dir = Path(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)

            update_config(
                cache_mode=self.settings.NFLREADPY_CACHE_MODE,
                cache_dir=self.settings.NFLREADPY_CACHE_DIR,
                verbose=self.settings.NFLREADPY_CACHE_VERBOSE,
                timeout=self.settings.NFLREADPY_TIMEOUT,
            )
            logger.info(
                f"nflreadpy caching enabled: {self.settings.NFLREADPY_CACHE_MODE} -> {self.settings.NFLREADPY_CACHE_DIR}"
            )
        else:
            logger.info("nflreadpy caching disabled")

        self.TEAM_COLORS = {}
        self.TEAM_LOGO_PATHS = {}
        self.preload_teams_data()
        super().__init__()

    @property
    def name(self) -> str:
        return "datasource_nflreadpy"

    def get_player_stats(
        self,
        seasons: list[int],
        summary_level: Literal["week", "reg", "post", "reg+post"] = "reg",
        players: list[str] | None = None,
        position: str | None = None,
        stats: list[str] | None = None,
    ) -> pd.DataFrame:
        try:
            logger.info(f"Retrieving Player stats for {seasons=}, {summary_level=}")

            result = nfl.load_player_stats(
                seasons=seasons,
                summary_level=summary_level,
            ).to_pandas()

            if result.empty:
                logger.error(f"No player stats found for seasons: {seasons}")
                return result

            if position and not result.empty:
                _before = len(result)
                result = result[result["position"] == position.upper()].copy()
                logger.info(f"Filtered by position {position=}, rows {_before} -> {len(result)}")

            if players:
                _before = len(result)
                result = result[result["player_display_name"].str.strip().isin(players)].copy()
                logger.info(f"Filtered by players {players=}, rows {_before} -> {len(result)}")

            if stats:
                _before = len(result.columns)
                valid_stats = [s for s in stats if s in result.columns]
                result = result[valid_stats]
                logger.info(f"Filtered by stats {stats=}, cols {_before} -> {len(result.columns)}")

            logger.info(
                f"Retrieved dataframe with rows: {len(result)} cols: {list(result.columns)}"
            )
            return result

        except Exception as e:
            logger.error(f"Error retrieving player stats from nflreadpy: {e}")
            raise RetrievalError(message=f"Failed to retrieve player stats: {str(e)}") from e

    def get_team_stats(
        self,
        seasons: list[int],
        summary_level: Literal["week", "reg", "post", "reg+post"] = "reg",
        teams: list[str] | None = None,
        stats: list[str] | None = None,
    ) -> pd.DataFrame:
        try:
            logger.info(f"Retrieving Team stats for {teams=}, {seasons=}, {summary_level=}")

            df = nfl.load_team_stats(
                seasons=seasons,
                summary_level=summary_level,
            ).to_pandas()

            if df.empty:
                raise ValueError(f"Team '{teams}' not found in nflreadpy data for {seasons=}")

            if teams and "ALL" not in teams:
                _before = len(df)
                df = df[df["team"].str.strip().isin([team.upper() for team in teams])].copy()
                logger.info(f"Filtered by teams {teams=}, rows {_before} -> {len(df)}")

            if stats:
                _before = len(df.columns)
                # Only select stats that exist in the dataframe
                valid_stats = [s for s in stats if s in df.columns]
                df = df[valid_stats]
                logger.info(f"Filtered by stats {stats=}, cols {_before} -> {len(df.columns)}")

            logger.info(f"Retrieved dataframe shape {df.shape} cols: {list(df.columns)}")
            return df

        except Exception as e:
            logger.error(f"Error retrieving team stats from nflreadpy: {e}")
            raise RetrievalError(message=f"Failed to retrieve team stats: {str(e)}") from e

    def preload_teams_data(self) -> None:
        try:
            logger.info("Preloading teams data from nflreadpy")
            teams = nfl.load_teams().to_pandas()

            logos_dir = self.settings.DATA_DIR / "logos"
            logos_dir.mkdir(parents=True, exist_ok=True)

            logo_files = list(logos_dir.glob("*.png"))
            if len(logo_files) >= len(teams):
                self.logos_preloaded = True

            for _, row in teams.iterrows():
                # Skip logo download for VCR testing
                team_abbr = row["team_abbr"]
                colors = []
                if pd.notna(row.get("team_color")):
                    colors.append(row["team_color"])
                if pd.notna(row.get("team_color2")):
                    colors.append(row["team_color2"])
                self.TEAM_COLORS[team_abbr] = colors

                logo_url = str(row["team_logo_espn"])
                logo_path = logos_dir / f"{team_abbr}.png"
                urlretrieve(logo_url, str(logo_path))
                if not self.logos_preloaded:
                    urlretrieve(row["team_logo_espn"], str(logo_path))
                self.TEAM_LOGO_PATHS[team_abbr] = str(logo_path)
            self.logos_preloaded = True
            logger.info("Teams data preloaded successfully")
        except Exception as e:
            logger.error(f"Error preloading teams data: {e}")

    def get_rosters(
        self,
        seasons: list[int],
    ) -> pd.DataFrame:
        try:
            logger.info(f"Retrieving rosters for {seasons=}")
            df = nfl.load_rosters(seasons=seasons).to_pandas()
            logger.info(f"Retrieved rosters shape {df.shape} cols: {list(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"Error retrieving rosters from nflreadpy: {e}")
            raise RetrievalError(message=f"Failed to retrieve rosters: {str(e)}") from e

    def get_snap_counts(
        self,
        seasons: list[int],
    ) -> pd.DataFrame:
        try:
            logger.info(f"Retrieving snap counts for {seasons=}")
            df = nfl.load_snap_counts(seasons=seasons).to_pandas()
            logger.info(f"Retrieved snap counts shape {df.shape} cols: {list(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"Error retrieving snap counts from nflreadpy: {e}")
            raise RetrievalError(message=f"Failed to retrieve snap counts: {str(e)}") from e

    def get_player_data(
        self,
    ) -> pd.DataFrame:
        try:
            logger.info("Retrieving player data")
            df = nfl.load_players().to_pandas()
            logger.info(f"Retrieved player data shape {df.shape} cols: {list(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"Error retrieving player data from nflreadpy: {e}")
            raise RetrievalError(message=f"Failed to retrieve player data: {str(e)}") from e
