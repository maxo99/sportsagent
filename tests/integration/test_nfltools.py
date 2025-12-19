from sportsagent.models.parsedquery import PlayerStatsQuery, TeamStatsQuery, TimePeriod
from sportsagent.nodes.retriever.retrievernode import fetch_player_statistics, fetch_team_statistics


def test_get_player_stats():
    player_name = "Kyle Pitts"
    season = 2024  # Using 2024 as 2025 might not have data yet or be partial

    query = PlayerStatsQuery(players=[player_name], timePeriod=TimePeriod(seasons=[season]))

    df = fetch_player_statistics(query)

    assert df is not None, "DataFrame should not be None"
    assert not df.empty, "DataFrame should not be empty for a known player"
    assert "receiving_yards" in df.columns, "DataFrame should contain 'receiving_yards' column"
    assert "receiving_tds" in df.columns, "DataFrame should contain 'receiving_tds' column"


def test_get_team_stats():
    # Test retrieving stats for a known team
    team_abbr = "KC"
    season = 2024

    query = TeamStatsQuery(teams=[team_abbr], timePeriod=TimePeriod(seasons=[season]))

    df = fetch_team_statistics(query)

    assert df is not None, "DataFrame should not be None"
    assert not df.empty, "DataFrame should not be empty for a known team"
    assert "team" in df.columns, "DataFrame should contain 'team' column"
    # Verify all rows are for the requested team
    assert (df["team"] == team_abbr).all(), f"All rows should be for team {team_abbr}"


def test_get_team_stats_all():
    # Test retrieving stats for all teams
    season = 2024

    query = TeamStatsQuery(teams=["ALL"], timePeriod=TimePeriod(seasons=[season]))

    df = fetch_team_statistics(query)

    assert df is not None, "DataFrame should not be None"
    assert not df.empty, "DataFrame should not be empty for ALL teams"
    assert "team" in df.columns, "DataFrame should contain 'team' column"
    # Verify we have multiple teams
    assert df["team"].nunique() > 1, "Should have data for multiple teams"
