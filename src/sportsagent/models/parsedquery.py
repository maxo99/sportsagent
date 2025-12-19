import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sportsagent.constants import (
    CURRENT_SEASON,
    PLAYER_STATS_COMMON,
    POSITION_STATS_MAP,
    STAT_MAPPINGS,
    TEAM_ABBREVIATIONS,
    TEAM_MAPPINGS,
    TEAMS_STATS_COMMON,
    TEAMS_STATS_MAP,
)


# Helper to clean strings for filenames
def _clean(s: str) -> str:
    return "".join(c for c in s if c.isalnum()).strip()


class TimePeriod(BaseModel):
    seasons: list[int] = Field(
        default=[CURRENT_SEASON], description="NFL seasons year (e.g., [2025] for 2025 season)"
    )
    # specific_weeks: list[int] | None = Field(default=None, description="Specific week numbers")
    # career: bool = Field(default=False, description="Whether to query career statistics")
    summary_level: Literal["week", "reg", "post", "reg+post"] = Field(
        default="reg",
        description='choice: one of week (default), "reg" for regular season, "post" for postseason, "reg+post" for combined regular season + postseason stats',
    )


class QueryFilters(BaseModel):
    opponent: str | None = Field(default=None, description="Opponent team")
    home_away: str | None = Field(default=None, description="'home', 'away', or None")
    min_value: float | None = Field(default=None, description="Minimum value for statistics")
    max_value: float | None = Field(default=None, description="Maximum value for statistics")
    situation: str | None = Field(
        default=None,
        description="Game situation (e.g., 'under_pressure', 'red_zone')",
    )


class StatisticsQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    statistics: list[str] = Field(
        default_factory=list,
        description="Statistical categories requested (e.g., 'passing_yards', 'touchdowns', 'completion_rate')",
    )
    tp: TimePeriod = Field(
        default_factory=TimePeriod,
        description="Time period for the query",
        alias="timePeriod",
    )


class ChartSpec(BaseModel):
    x_axis: str = Field(description="Column name for the x-axis")
    y_axis: str = Field(description="Column name for the y-axis")
    group_by: str | None = Field(
        default=None, description="Column name for grouping (color/legend)"
    )
    aggregation: Literal["sum", "mean", "max", "min", "count"] | None = Field(
        default=None, description="Aggregation to apply to y-axis"
    )
    title: str | None = Field(default=None, description="Title for the chart")


class RetrievalMergeIntent(BaseModel):
    mode: Literal["replace", "append"] = Field(
        default="replace", description="Whether to replace current data or append to it"
    )


class EnrichmentOptions(BaseModel):
    filters: dict[str, Any] = Field(default_factory=dict)
    join_keys: list[str] = Field(default_factory=list)


class PlayerStatsQuery(StatisticsQuery):
    players: list[str] | None = Field(
        default=None,
        description="List of specific player names mentioned",
    )
    position: str | None = Field(
        default=None,
        description="Position mentioned (e.g., ALL, QB, RB, WR, TE, K)",
    )
    teams: list[str] = Field(
        default_factory=list,
        description="List of team names mentioned",
    )

    @field_validator("players", mode="before")
    def validate_players(cls, v):
        if not v:
            return v
        # Normalize player names
        for i, player_name in enumerate(v):
            normalized_name = normalize_player_name(player_name)
            v[i] = normalized_name
        # Remove duplicates while preserving order
        unique_players = list(dict.fromkeys(v))
        return unique_players

    @field_validator("position", mode="before")
    def validate_position(cls, v):
        if v is None:
            return v
        return v.upper()

    @field_validator("statistics", mode="before")
    def validate_statistics(cls, v):
        if not v:
            return v
        return normalize_stat_names(v)

    @property
    def queryName(self) -> str:
        """
        Returns a concise name for the type of query based on intent.
        """
        parts = []

        if self.position:
            # parts.append("-".join(_clean(p) for p in self.position))
            parts.append(self.position)

        if self.players:
            # Limit to 3 players to keep name short
            parts.append("-".join(_clean(p) for p in self.players[:3]))
            if len(self.players) > 3:
                parts.append(f"and_{len(self.players) - 3}_more")

        if self.teams:
            parts.append("-".join(_clean(t) for t in self.teams[:3]))

        if self.statistics:
            # Limit to 2 stats
            parts.append("-".join(_clean(s) for s in self.statistics[:2]))

        if self.tp.seasons:
            parts.append("-".join(str(p) for p in self.tp.seasons))
            # parts.append(f"{self.tp.seasons}")

        # if self.comparison:
        #     parts.append("comp")

        return "_".join(parts) or "general_query"

    @property
    def stats_cols(self) -> list[str]:
        """
        Returns a list of statistics columns relevant to the query.
        """
        if self.statistics:
            return [*PLAYER_STATS_COMMON, *self.statistics]
        if self.position:
            return POSITION_STATS_MAP.get(self.position, [])
        return POSITION_STATS_MAP.get("ALL", [])


class TeamStatsQuery(StatisticsQuery):
    teams: list[str] = Field(default=["ALL"], description="List of team names mentioned")

    @property
    def queryName(self) -> str:
        """
        Returns a concise name for the type of query based on intent.
        """
        parts = []

        if self.teams:
            parts.append("-".join(_clean(t) for t in self.teams[:3]))

        if self.statistics:
            # Limit to 2 stats
            parts.append("-".join(_clean(s) for s in self.statistics[:2]))

        if self.tp.seasons:
            parts.append("-".join(str(p) for p in self.tp.seasons))

        # if self.comparison:
        #     parts.append("comp")

        return "_".join(parts) or "general_query"

    @field_validator("teams", mode="before")
    def validate_teams(cls, v):
        if not v:
            return v
        # Normalize team names
        for i, team_name in enumerate(v):
            if team_name not in [*TEAM_ABBREVIATIONS, "ALL"]:
                normalized_name = TEAM_MAPPINGS.get(team_name.lower(), team_name)
                v[i] = normalized_name
            else:
                v[i] = team_name.upper()
        # Remove duplicates while preserving order
        unique_teams = list(dict.fromkeys(v))
        return unique_teams

    @property
    def stats_cols(self) -> list[str]:
        """
        Returns a list of statistics columns relevant to the query.
        """
        if self.statistics:
            return [*TEAMS_STATS_COMMON, *self.statistics]
        return TEAMS_STATS_MAP.get("ALL", [])


class ParsedQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_stats_query: PlayerStatsQuery | None = Field(
        default=None,
        description="Details specific to player statistics queries",
    )
    team_stats_query: TeamStatsQuery | None = Field(
        default=None,
        description="Details specific to team statistics queries",
    )
    chart_spec: "ChartSpec | None" = Field(
        default=None,
        description="Specifications for generating a chart",
        alias="chartSpec",
    )
    retrieval_merge_intent: "RetrievalMergeIntent" = Field(
        default_factory=lambda: RetrievalMergeIntent(mode="replace"),
        description="Whether to replace current data or append to it",
        alias="retrievalMergeIntent",
    )
    enrichment_options: "EnrichmentOptions" = Field(
        default_factory=lambda: EnrichmentOptions(),
        description="Options for data enrichment",
        alias="enrichmentOptions",
    )

    clarification_question: str | None = Field(
        default=None,
        description="Question to ask user for clarification if parse_status is 'needs_clarification'",
    )
    parse_status: Literal["unparsed", "needs_clarification", "parsed"] = Field(
        default="unparsed",
        description="Status of the parsing process",
    )
    query_intent: str = Field(
        default="player_stats",
        description="Intent: 'player_stats', 'team_stats' ",
    )

    workflow_intent: Literal["retrieve", "rechart", "enrich"] = Field(
        default="retrieve",
        description="Workflow intent: retrieve new base stats, rechart using existing data, or enrich existing data.",
        alias="workflowIntent",
    )
    wants_visualization: bool = Field(
        default=False,
        description="Whether the user is asking for a chart/plot.",
        alias="wantsVisualization",
    )
    enrichment_datasets: list[
        Literal["rosters", "snap_counts", "schedules", "participation", "player_info"]
    ] = Field(
        default_factory=list,
        description="Optional enrichment datasets to fetch and attach to retrieved_data.",
        alias="enrichmentDatasets",
    )

    @property
    def queryName(self) -> str:
        """
        Returns a concise name for the type of query based on intent.
        """
        parts = []

        if self.team_stats_query:
            parts.append("teamstats-" + self.team_stats_query.queryName)
        if self.player_stats_query:
            parts.append("playerstats-" + self.player_stats_query.queryName)
        # if self.comparison:
        #     parts.append("comp")

        return "_".join(parts) or "general_query"

    @property
    def needs_clarification(self) -> bool:
        return self.parse_status == "needs_clarification"


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
