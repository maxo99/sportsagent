import os

import pytest

from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.nodes.queryparser.queryparsernode import query_parser_node


def _enabled() -> bool:
    return os.environ.get("RUN_LIVE_LLM_TESTS", "0") == "1" and bool(
        os.environ.get("OPENAI_API_KEY")
    )


pytestmark = pytest.mark.skipif(
    not _enabled(),
    reason="Live LLM tests are disabled. Set RUN_LIVE_LLM_TESTS=1 and OPENAI_API_KEY.",
)


def _state(user_query: str, conversation_history: list[dict]) -> ChatbotState:
    return ChatbotState(
        session_id="live",
        user_query=user_query,
        generated_response="",
        conversation_history=conversation_history,
        retrieved_data=None,
    )


def test_query_battery_live_rechart_followup_resolves_to_rechart() -> None:
    history = [
        {
            "content": "Show me Josh Allen passing yards for 2024",
            "response": "Ok",
            "mentioned_players": ["Josh Allen"],
            "mentioned_players_stats": ["passing_yards"],
        }
    ]

    state = query_parser_node(_state("Now make it a scatter plot", history))

    assert state.error is None
    assert state.parsed_query.parse_status == "parsed"
    assert state.parsed_query.workflow_intent == "rechart"
    assert state.parsed_query.wants_visualization is True
    assert state.parsed_query.player_stats_query is None
    assert state.parsed_query.team_stats_query is None


def test_query_battery_live_instead_show_stat_is_retrieve_not_rechart() -> None:
    history = [
        {
            "content": "Show me Josh Allen passing yards for 2024",
            "response": "Ok",
            "mentioned_players": ["Josh Allen"],
            "mentioned_players_stats": ["passing_yards"],
        }
    ]

    state = query_parser_node(_state("Instead show me rushing yards", history))

    assert state.error is None
    assert state.parsed_query.parse_status == "parsed"
    assert state.pending_action in {"retrieve", "enrich"}
    assert state.pending_action != "rechart"
    assert (
        (state.parsed_query.player_stats_query is not None)
        or (state.parsed_query.team_stats_query is not None)
        or bool(state.parsed_query.enrichment_datasets)
    )
