
from sportsagent.models.chatboterror import ErrorStates
from sportsagent.models.parsedquery import ParsedQuery, PlayerStatsQuery, TimePeriod
from sportsagent.nodes.retriever.retrievernode import retriever_node


def test_retriever_node_player_lookup(base_state, player_stats_parsed_query):
    """Test that retriever_node correctly fetches data for a specific player."""
    base_state.parsed_query = player_stats_parsed_query

    result_state = retriever_node(base_state)

    assert result_state.error is None
    assert result_state.retrieved_data is not None
    assert len(result_state.retrieved_data.players) > 0

    # Verify specific player data
    player_records = result_state.retrieved_data.players
    assert any(r.get("player_display_name") == "Josh Allen" for r in player_records)


def test_retriever_node_position_lookup(base_state):
    """Test that retriever_node correctly fetches data for a position (migrated from manual test)."""
    base_state.parsed_query = ParsedQuery(
        query_intent="player_stats",
        workflowIntent="retrieve",
        player_stats_query=PlayerStatsQuery(
            position="QB",
            statistics=["passing_yards"],
            timePeriod=TimePeriod(seasons=[2024], summary_level="reg"),
        ),
    )

    result_state = retriever_node(base_state)

    assert result_state.error is None
    assert result_state.retrieved_data is not None

    player_records = result_state.retrieved_data.players
    assert len(player_records) > 0
    # All records should be QBs
    assert all(r.get("position") == "QB" for r in player_records)


def test_retriever_node_team_lookup(base_state, team_stats_parsed_query):
    """Test that retriever_node correctly fetches data for a team."""
    base_state.parsed_query = team_stats_parsed_query

    result_state = retriever_node(base_state)

    assert result_state.error is None
    assert result_state.retrieved_data is not None
    assert len(result_state.retrieved_data.teams) > 0

    team_records = result_state.retrieved_data.teams
    assert all(r.get("team") == "KC" for r in team_records)


def test_retriever_node_no_data_found(base_state):
    """Test that retriever_node handles cases where no data is found."""
    base_state.parsed_query = ParsedQuery(
        query_intent="player_stats",
        workflowIntent="retrieve",
        player_stats_query=PlayerStatsQuery(
            players=["NonExistentPlayerXYZ"],
            statistics=["passing_yards"],
            timePeriod=TimePeriod(seasons=[2024], summary_level="reg"),
        ),
    )

    result_state = retriever_node(base_state)

    assert result_state.error == ErrorStates.NO_DATA_FOUND
    if isinstance(result_state.generated_response, str):
        assert "No statistics found" in result_state.generated_response


def test_retriever_node_enrichment(base_state):
    """Test that retriever_node handles enrichment requests (e.g., rosters)."""
    base_state.pending_action = "enrich"
    base_state.parsed_query = ParsedQuery(
        query_intent="general_query", workflowIntent="enrich", enrichmentDatasets=["rosters"]
    )

    result_state = retriever_node(base_state)

    assert result_state.error is None
    assert result_state.retrieved_data is not None
    assert "rosters" in result_state.retrieved_data.extra
    assert len(result_state.retrieved_data.extra["rosters"]) > 0
