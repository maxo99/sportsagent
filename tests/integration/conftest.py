import pytest

from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.parsedquery import ParsedQuery, PlayerStatsQuery, TeamStatsQuery, TimePeriod


@pytest.fixture
def base_state():
    return ChatbotState(
        session_id="test_session",
        user_query="test query",
        generated_response="",
    )


@pytest.fixture
def player_stats_parsed_query():
    return ParsedQuery(
        query_intent="player_stats",
        workflowIntent="retrieve",
        player_stats_query=PlayerStatsQuery(
            players=["Josh Allen"],
            statistics=["passing_yards"],
            timePeriod=TimePeriod(seasons=[2024], summary_level="reg"),
        ),
    )


@pytest.fixture
def team_stats_parsed_query():
    return ParsedQuery(
        query_intent="team_stats",
        workflowIntent="retrieve",
        team_stats_query=TeamStatsQuery(
            teams=["KC"],
            statistics=["passing_yards"],
            timePeriod=TimePeriod(seasons=[2024], summary_level="reg"),
        ),
    )
