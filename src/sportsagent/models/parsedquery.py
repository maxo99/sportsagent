from pydantic import BaseModel, Field


class TimePeriod(BaseModel):
    season: int | None = Field(default=None, description="NFL season year (e.g., 2023)")
    week: int | None = Field(default=None, description="Week number (1-18)")
    start_week: int | None = Field(default=None, description="Starting week number (1-18)")
    end_week: int | None = Field(default=None, description="Ending week number (1-18)")
    specific_weeks: list[int] | None = Field(default=None, description="Specific week numbers")
    career: bool = Field(default=False, description="Whether to query career statistics")


class QueryFilters(BaseModel):
    opponent: str | None = Field(default=None, description="Opponent team")
    home_away: str | None = Field(default=None, description="'home', 'away', or None")
    min_value: float | None = Field(default=None, description="Minimum value for statistics")
    max_value: float | None = Field(default=None, description="Maximum value for statistics")
    situation: str | None = Field(
        default=None,
        description="Game situation (e.g., 'under_pressure', 'red_zone')",
    )


class ParsedQuery(BaseModel):
    players: list[str] = Field(default_factory=list, description="List of player names mentioned")
    positions: list[str] = Field(
        default_factory=list, description="List of positions mentioned (e.g., QB, RB, WR)"
    )
    teams: list[str] = Field(default_factory=list, description="List of team names mentioned")
    statistics: list[str] = Field(
        default_factory=list,
        description="Statistical categories requested (e.g., 'passing_yards', 'touchdowns', 'completion_rate')",
    )
    time_period: TimePeriod = Field(
        default_factory=TimePeriod,
        description="Time period for the query",
    )
    filters: QueryFilters = Field(
        default_factory=QueryFilters,
        description="Additional query filters",
    )
    comparison: bool = Field(
        default=False,
        description="Whether this is a comparison query",
    )
    aggregation: str | None = Field(
        default=None,
        description="Aggregation type: 'sum', 'average', 'max', 'min'",
    )
    needs_clarification: bool = Field(
        default=False,
        description="Whether the query is ambiguous and needs clarification",
    )
    clarification_question: str | None = Field(
        default=None,
        description="Question to ask user for clarification",
    )
    query_intent: str = Field(
        default="player_stats",
        description="Intent: 'player_stats', 'comparison', 'ranking', 'trend_analysis'",
    )

    @property
    def queryName(self) -> str:
        """
        Returns a concise name for the type of query based on intent.
        """
        parts = []

        # Helper to clean strings for filenames
        def clean(s: str) -> str:
            return "".join(c for c in s if c.isalnum()).strip()

        if self.positions:
            parts.append("-".join(clean(p) for p in self.positions))

        if self.players:
            # Limit to 3 players to keep name short
            parts.append("-".join(clean(p) for p in self.players[:3]))
            if len(self.players) > 3:
                parts.append(f"and_{len(self.players)-3}_more")

        if self.teams:
            parts.append("-".join(clean(t) for t in self.teams[:3]))

        if self.statistics:
            # Limit to 2 stats
            parts.append("-".join(clean(s) for s in self.statistics[:2]))

        if self.time_period.season:
            parts.append(f"{self.time_period.season}")

        if self.comparison:
            parts.append("comp")

        return "_".join(parts) or "general_query"
