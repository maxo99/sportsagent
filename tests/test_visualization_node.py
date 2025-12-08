import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import plotly.graph_objects as go
from sportsagent.nodes.visualizationnode import visualization_node
from sportsagent.models.chatbotstate import ChatbotState


@pytest.fixture
def mock_state():
    state = MagicMock(spec=ChatbotState)
    state.needs_visualization = True
    state.retrieved_data = [{"col1": 1, "col2": 10}, {"col1": 2, "col2": 20}]
    state.user_query = "Show me a chart"
    state.visualization = None
    return state


@patch("sportsagent.nodes.visualizationnode.ChatOpenAI")
def test_visualization_node_success(mock_chat_openai, mock_state):
    # Mock the LLM chain response
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm

    # Mock the invoke method to return a valid python function string
    mock_chain = MagicMock()
    mock_llm.__or__.return_value = mock_chain

    code_response = """
def generate_plot(df):
    import plotly.express as px
    fig = px.bar(df, x='col1', y='col2')
    return fig
"""
    mock_chain.invoke.return_value = code_response

    # Execute the node
    new_state = visualization_node(mock_state)

    # Verify that the state was updated with a figure
    assert new_state.visualization is not None
    assert isinstance(new_state.visualization, go.Figure)


@patch("sportsagent.nodes.visualizationnode.ChatOpenAI")
def test_visualization_node_no_data(mock_chat_openai, mock_state):
    mock_state.retrieved_data = []

    new_state = visualization_node(mock_state)

    assert new_state.visualization is None


@patch("sportsagent.nodes.visualizationnode.ChatOpenAI")
def test_visualization_node_not_needed(mock_chat_openai, mock_state):
    mock_state.needs_visualization = False

    new_state = visualization_node(mock_state)

    assert new_state.visualization is None
