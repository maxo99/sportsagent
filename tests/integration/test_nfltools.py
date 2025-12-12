import nflreadpy as nfl

from sportsagent.datasource.nflreadpy import NFLReadPyDataSource


def test_columns():
    data = nfl.load_player_stats(seasons=[2024]).to_pandas()
    print(data)


def test_get_player_stats():
    # Test retrieving stats for a known player
    player_name = "Kyle Pitts"
    season = 2025
    # week = 1
    # stats = ["passing_yards", "touchdowns"]

    datasource = NFLReadPyDataSource()
    df = datasource.get_player_stats(
        player_name=player_name,
        season=season,
    )

    assert not df.empty, "DataFrame should not be empty for a known player"
    assert "passing_yards" in df.columns, "DataFrame should contain 'passing_yards' column"
    assert "touchdowns" in df.columns, "DataFrame should contain 'touchdowns' column"
