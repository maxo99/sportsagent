from unittest.mock import MagicMock, patch

import pandas as pd

from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.retrieveddata import RetrievedData
from sportsagent.nodes.analyzer.analyzernode import analyzer_node


@patch("sportsagent.nodes.analyzer.analyzernode.AnalyzerAgent")
def test_analyzer_node_handles_dict_data(mock_agent_cls):
    # Setup mock agent
    mock_agent = MagicMock()
    mock_agent.get_tool_calls.return_value = []
    mock_agent.get_ai_message.return_value = "Analysis complete."
    mock_agent_cls.return_value = mock_agent

    # Setup state with dict data
    state = ChatbotState(
        session_id="test",
        user_query="analyze this",
        retrieved_data=RetrievedData(
            players=[{"name": "P1", "yards": 100}],
            teams=[{"team": "T1", "wins": 5}],
        ),
        generated_response="",
    )

    # Run node
    analyzer_node(state)

    # Verify agent was called
    mock_agent.invoke_agent.assert_called_once()

    # Verify primary_df selection logic (should prefer players)
    call_args = mock_agent.invoke_agent.call_args
    data_raw = call_args.kwargs["data_raw"]
    assert isinstance(data_raw, pd.DataFrame)
    assert "name" in data_raw.columns  # Should be the players dataframe


@patch("sportsagent.nodes.analyzer.analyzernode.AnalyzerAgent")
def test_analyzer_node_handles_teams_only(mock_agent_cls):
    # Setup mock agent
    mock_agent = MagicMock()
    mock_agent.get_tool_calls.return_value = []
    mock_agent.get_ai_message.return_value = "Analysis complete."
    mock_agent_cls.return_value = mock_agent

    # Setup state with only teams data
    state = ChatbotState(
        session_id="test",
        user_query="analyze teams",
        retrieved_data=RetrievedData(teams=[{"team": "T1", "wins": 5}]),
        generated_response="",
    )

    # Run node
    analyzer_node(state)

    # Verify primary_df selection logic
    call_args = mock_agent.invoke_agent.call_args
    data_raw = call_args.kwargs["data_raw"]
    assert isinstance(data_raw, pd.DataFrame)
    assert "team" in data_raw.columns
