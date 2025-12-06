from datetime import datetime

CURRENT_YEAR = datetime.now().year
CURRENT_SEASON = CURRENT_YEAR if datetime.now().month >= 9 else CURRENT_YEAR - 1


# Mapping of common stat name variations to standardized names
STAT_MAPPINGS = {
    # Passing stats
    "passing yards": "passing_yards",
    "pass yards": "passing_yards",
    "yards": "passing_yards",  # Default to passing if ambiguous
    "completions": "completions",
    "attempts": "attempts",
    "completion percentage": "completion_rate",
    "completion rate": "completion_rate",
    "comp %": "completion_rate",
    "touchdowns": "passing_touchdowns",
    "tds": "passing_touchdowns",
    "passing tds": "passing_touchdowns",
    "interceptions": "interceptions",
    "ints": "interceptions",
    "picks": "interceptions",
    "sacks": "sacks",
    "yards per attempt": "yards_per_attempt",
    "ypa": "yards_per_attempt",
    # Rushing stats
    "rushing yards": "rushing_yards",
    "rush yards": "rushing_yards",
    "carries": "rushing_attempts",
    "rushing attempts": "rushing_attempts",
    "rushing touchdowns": "rushing_touchdowns",
    "rushing tds": "rushing_touchdowns",
    "yards per carry": "yards_per_carry",
    "ypc": "yards_per_carry",
    # Receiving stats
    "receiving yards": "receiving_yards",
    "rec yards": "receiving_yards",
    "receptions": "receptions",
    "catches": "receptions",
    "targets": "targets",
    "receiving touchdowns": "receiving_touchdowns",
    "receiving tds": "receiving_touchdowns",
    "yards per reception": "yards_per_reception",
    "ypr": "yards_per_reception",
    # Advanced metrics
    "epa": "epa",
    "expected points added": "epa",
}


TEAM_MAPPINGS = {
    "chiefs": "Kansas City Chiefs",
    "kc": "Kansas City Chiefs",
    "kansas city": "Kansas City Chiefs",
    "bills": "Buffalo Bills",
    "buffalo": "Buffalo Bills",
    "bengals": "Cincinnati Bengals",
    "cincinnati": "Cincinnati Bengals",
    "49ers": "San Francisco 49ers",
    "niners": "San Francisco 49ers",
    "san francisco": "San Francisco 49ers",
    "cowboys": "Dallas Cowboys",
    "dallas": "Dallas Cowboys",
    "eagles": "Philadelphia Eagles",
    "philadelphia": "Philadelphia Eagles",
    "philly": "Philadelphia Eagles",
}
