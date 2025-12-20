from __future__ import annotations

from typing import Any
from unittest.mock import patch

from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.parsedquery import ParsedQuery, PlayerStatsQuery, TeamStatsQuery, TimePeriod
from sportsagent.models.retrieveddata import RetrievedData
from sportsagent.nodes.queryparser.queryparsernode import (
    _extract_context_from_history,
    query_parser_node,
)
from sportsagent.routing import should_continue_after_parser


class _DummyStructuredLLM:
    def __init__(self, parsed: ParsedQuery):
        self._parsed = parsed

    def with_structured_output(self, schema: type[Any], **kwargs: Any) -> _DummyStructuredLLM:  # noqa: ARG002
        return self

    def invoke(self, input: Any, temperature: float = 0) -> ParsedQuery:  # noqa: ARG002
        return self._parsed


def _state(user_query: str) -> ChatbotState:
    return ChatbotState(
        session_id="test",
        user_query=user_query,
        generated_response="",
        conversation_history=[],
        retrieved_data=None,
    )


def test_query_parser_node_sets_pending_action_and_visualization_flag_for_retrieve() -> None:
    parsed = ParsedQuery(
        workflowIntent="retrieve",
        wantsVisualization=True,
        query_intent="player_stats",
        player_stats_query=PlayerStatsQuery(
            players=["Josh Allen"],
            statistics=["passing_yards"],
            timePeriod=TimePeriod(seasons=[2024]),
        ),
    )

    with patch(
        "sportsagent.nodes.queryparser.queryparsernode.ChatOpenAI",
        return_value=_DummyStructuredLLM(parsed),
    ):
        state = query_parser_node(_state("Show me Josh Allen passing yards 2024 as a chart"))

    assert state.parsed_query.workflow_intent == "retrieve"
    assert state.pending_action == "retrieve"
    assert state.needs_visualization is True


def test_query_parser_node_overrides_rechart_if_it_includes_stats_query() -> None:
    parsed = ParsedQuery(
        workflowIntent="rechart",
        wantsVisualization=True,
        query_intent="player_stats",
        player_stats_query=PlayerStatsQuery(
            players=["Josh Allen"],
            statistics=["passing_yards"],
            timePeriod=TimePeriod(seasons=[2024]),
        ),
    )

    with patch(
        "sportsagent.nodes.queryparser.queryparsernode.ChatOpenAI",
        return_value=_DummyStructuredLLM(parsed),
    ):
        state = query_parser_node(_state("Instead show Josh Allen passing yards 2024"))

    assert state.parsed_query.workflow_intent == "rechart"
    assert state.pending_action == "retrieve"


def test_query_parser_node_overrides_rechart_to_enrich_if_enrichment_present() -> None:
    parsed = ParsedQuery(
        workflowIntent="rechart",
        wantsVisualization=True,
        enrichmentDatasets=["snap_counts"],
        query_intent="team_stats",
        team_stats_query=TeamStatsQuery(
            teams=["ALL"],
            statistics=["passing_yards"],
            timePeriod=TimePeriod(seasons=[2024]),
        ),
    )

    with patch(
        "sportsagent.nodes.queryparser.queryparsernode.ChatOpenAI",
        return_value=_DummyStructuredLLM(parsed),
    ):
        state = query_parser_node(_state("Add snap counts and rechart"))

    assert state.parsed_query.workflow_intent == "rechart"
    assert state.pending_action == "enrich"


def test_should_continue_after_parser_exits_on_rechart_without_loaded_data() -> None:
    state = _state("Make it a scatter plot")
    state.parsed_query = ParsedQuery(workflowIntent="rechart", wantsVisualization=True)
    state.pending_action = "rechart"

    nxt = should_continue_after_parser(state)

    assert nxt == "exit"
    assert isinstance(state.generated_response, str)
    assert "don't have any data loaded" in state.generated_response.lower()


def test_should_continue_after_parser_routes_to_visualization_for_rechart_when_data_loaded() -> (
    None
):
    state = _state("Make it a scatter plot")
    state.parsed_query = ParsedQuery(workflowIntent="rechart", wantsVisualization=True)
    state.pending_action = "rechart"
    state.retrieved_data = RetrievedData(players=[{"player": "X"}])

    nxt = should_continue_after_parser(state)

    assert nxt == "generate_visualization"


def test_extract_context_from_history_supports_turn_and_message_styles() -> None:
    history = [
        {
            "content": "Show me Josh Allen passing yards 2024",
            "response": "Sure",
            "mentioned_players": ["Josh Allen"],
            "mentioned_players_stats": ["passing_yards"],
        },
        {"role": "user", "content": "Now make it a scatter plot"},
        {"role": "assistant", "content": "Ok"},
    ]

    context = _extract_context_from_history(history)

    assert "Josh Allen" in context["recent_players"]
    assert "passing_yards" in context["recent_stats"]
    assert any(m.startswith("User:") for m in context["messages"])
    assert any(m.startswith("Assistant:") for m in context["messages"])
