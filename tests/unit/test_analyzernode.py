from unittest.mock import MagicMock, patch

import pandas as pd

from sportsagent.models.analyzeroutput import AnalyzerOutput
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.retrieveddata import RetrievedData
from sportsagent.nodes.analyzer.analyzernode import analyzer_node


@patch("sportsagent.nodes.analyzer.analyzernode.AnalyzerAgent")
def test_analyzer_node_handles_dict_data(mock_agent_cls):
    mock_agent = MagicMock()
    mock_agent.get_tool_calls.return_value = []
    mock_agent.get_ai_message.return_value = "Analysis complete."
    mock_agent.response = {
        "structured_response": AnalyzerOutput(
            analysis="Data analysis details",
            judgment="Analysis complete.",
            visualization_request=None,
        ),
    }
    mock_agent_cls.return_value = mock_agent

    state = ChatbotState(
        session_id="test",
        user_query="analyze this",
        retrieved_data=RetrievedData(
            players=[{"name": "P1", "yards": 100}],
            teams=[{"team": "T1", "wins": 5}],
        ),
        generated_response="",
    )

    analyzer_node(state)

    # Verify agent was called
    mock_agent.invoke_agent.assert_called_once()

    call_args = mock_agent.invoke_agent.call_args
    data_raw = call_args.kwargs["data_raw"]
    assert isinstance(data_raw, pd.DataFrame)
    assert "name" in data_raw.columns

    assert state.analyzer_output is not None
    assert state.generated_response == "Analysis complete."


@patch("sportsagent.nodes.analyzer.analyzernode.AnalyzerAgent")
def test_analyzer_node_handles_teams_only(mock_agent_cls):
    mock_agent = MagicMock()
    mock_agent.get_tool_calls.return_value = []
    mock_agent.get_ai_message.return_value = "Analysis complete."
    mock_agent.response = {
        "structured_response": AnalyzerOutput(
            analysis="Team analysis details",
            judgment="Analysis complete.",
            visualization_request="Bar chart showing wins",
        ),
    }
    mock_agent_cls.return_value = mock_agent

    state = ChatbotState(
        session_id="test",
        user_query="analyze teams",
        retrieved_data=RetrievedData(teams=[{"team": "T1", "wins": 5}]),
        generated_response="",
    )

    analyzer_node(state)

    call_args = mock_agent.invoke_agent.call_args
    data_raw = call_args.kwargs["data_raw"]
    assert isinstance(data_raw, pd.DataFrame)
    assert "team" in data_raw.columns

    assert state.analyzer_output is not None
    assert state.analyzer_output.visualization_request == "Bar chart showing wins"


@patch("sportsagent.nodes.analyzer.analyzernode.AnalyzerAgent")
def test_analyzer_node_handles_missing_structured_output(mock_agent_cls):
    mock_agent = MagicMock()
    mock_agent.get_tool_calls.return_value = []
    mock_agent.get_ai_message.return_value = "Analysis complete."
    mock_agent.response = {}
    mock_agent_cls.return_value = mock_agent

    state = ChatbotState(
        session_id="test",
        user_query="analyze this",
        retrieved_data=RetrievedData(players=[{"name": "P1", "yards": 100}]),
        generated_response="",
    )

    analyzer_node(state)

    assert state.analyzer_output is None
    assert state.generated_response == "Analysis complete."
