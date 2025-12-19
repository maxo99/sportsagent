import pandas as pd
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.parsedquery import (
    ParsedQuery,
    ChartSpec,
    RetrievalMergeIntent,
    PlayerStatsQuery,
)
from sportsagent.nodes.retriever.retrievernode import aggregate_data, retrieve_data_sync
from sportsagent.models.retrieveddata import RetrievedData


def test_aggregate_data_with_chart_spec():
    # Setup data
    df = pd.DataFrame(
        {
            "player_name": ["Mahomes", "Mahomes", "Allen", "Allen"],
            "season": [2024, 2024, 2024, 2024],
            "passing_yards": [300, 250, 280, 320],
            "week": [1, 2, 1, 2],
        }
    )

    # Chart spec: sum passing yards by player
    spec = ChartSpec(x_axis="player_name", y_axis="passing_yards", aggregation="sum")

    aggregated = aggregate_data(df, spec)

    assert len(aggregated) == 2
    assert aggregated.loc[aggregated["player_name"] == "Mahomes", "passing_yards"].values[0] == 550
    assert aggregated.loc[aggregated["player_name"] == "Allen", "passing_yards"].values[0] == 600


def test_aggregate_data_with_group_by():
    # Setup data
    df = pd.DataFrame(
        {
            "player_name": ["Mahomes", "Mahomes", "Allen", "Allen"],
            "season": [2023, 2024, 2023, 2024],
            "passing_yards": [300, 250, 280, 320],
        }
    )

    # Chart spec: sum passing yards by player and season
    spec = ChartSpec(
        x_axis="player_name", y_axis="passing_yards", group_by="season", aggregation="sum"
    )

    aggregated = aggregate_data(df, spec)

    assert len(aggregated) == 4
    val = aggregated.loc[
        (aggregated["player_name"] == "Mahomes") & (aggregated["season"] == 2023), "passing_yards"
    ].values[0]
    assert val == 300


def test_parsed_query_defaults():
    pq = ParsedQuery()
    assert pq.retrieval_merge_intent.mode == "replace"
    assert pq.chart_spec is None
    assert pq.enrichment_options.filters == {}


def test_retrieve_data_append_mode(monkeypatch):
    # Setup mock data source
    from sportsagent.nodes.retriever import retrievernode

    df2 = pd.DataFrame([{"player_name": "Allen", "passing_yards": 280, "season": 2024}])

    # Simple mock that returns df2
    def mock_get_player_stats(*args, **kwargs):
        return df2

    monkeypatch.setattr(retrievernode.NFL_DATASOURCE, "get_player_stats", mock_get_player_stats)

    # Initial state with some data
    initial_players = [{"player_name": "Mahomes", "passing_yards": 300, "season": 2024}]
    state = ChatbotState(
        session_id="test",
        user_query="Mahomes stats",
        retrieved_data=RetrievedData(players=initial_players),
        generated_response="",
    )

    # New query with append mode
    state.parsed_query = ParsedQuery(
        player_stats_query=PlayerStatsQuery(players=["Allen"], statistics=["passing_yards"]),
        retrieval_merge_intent=RetrievalMergeIntent(mode="append"),
    )

    # Run retriever (using the sync wrapper)
    from sportsagent.nodes.retriever.retrievernode import retriever_node

    new_state = retriever_node(state)

    assert len(new_state.retrieved_data.players) == 2
    players = [r["player_name"] for r in new_state.retrieved_data.players]
    assert "Mahomes" in players
    assert "Allen" in players
