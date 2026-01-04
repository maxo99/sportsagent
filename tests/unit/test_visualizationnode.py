from unittest.mock import MagicMock, patch

import pytest

from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.nodes.visualization.visualizationnode import (
    execute_visualization_node,
    generate_visualization_node,
)


@pytest.fixture
def mock_state():
    state = MagicMock(spec=ChatbotState)
    state.needs_visualization = True
    state.retrieved_data = {"default": [{"col1": 1, "col2": 10}, {"col1": 2, "col2": 20}]}
    state.user_query = "Show me a chart"
    state.visualization = None
    state.visualization_code = None
    state.parsed_query = MagicMock()
    state.parsed_query.chart_spec = None
    return state


@patch("sportsagent.nodes.visualization.visualizationnode.get_datasource")
@patch("sportsagent.nodes.visualization.visualizationnode.ChatOpenAI")
def test_visualization_flow_success(mock_chat_openai, mock_get_datasource, mock_state):
    # Mock the datasource
    mock_datasource = MagicMock()
    mock_datasource.TEAM_COLORS = {"KC": ["#E31837", "#FFB612"]}
    mock_datasource.TEAM_LOGO_PATHS = {"KC": "data/logos/KC.png"}
    mock_get_datasource.return_value = mock_datasource

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

    # Execute the generation node
    state_after_gen = generate_visualization_node(mock_state)

    assert state_after_gen.visualization_code is not None

    # Execute the execution node
    final_state = execute_visualization_node(state_after_gen)

    # Verify that the state was updated with a figure
    assert final_state.visualization is not None
    assert isinstance(final_state.visualization, dict)


@patch("sportsagent.nodes.visualization.visualizationnode.ChatOpenAI")
def test_visualization_node_no_data(mock_chat_openai, mock_state):
    mock_state.retrieved_data = {}

    new_state = generate_visualization_node(mock_state)

    assert new_state.visualization_code is None


@patch("sportsagent.nodes.visualization.visualizationnode.ChatOpenAI")
def test_visualization_node_not_needed(mock_chat_openai, mock_state):
    mock_state.needs_visualization = False

    new_state = generate_visualization_node(mock_state)

    assert new_state.visualization_code is None


@patch("sportsagent.nodes.visualization.visualizationnode.get_datasource")
def test_execute_visualization_passes_team_data_to_globals(mock_get_datasource, mock_state):
    """Test that execute_visualization_node passes TEAM_COLORS, TEAM_LOGO_PATHS, and encode_team_logo to exec globals."""
    # Mock datasource with team data
    mock_datasource = MagicMock()
    mock_datasource.TEAM_COLORS = {"KC": ["#E31837", "#FFB612"], "BUF": ["#00338D", "#C60C30"]}
    mock_datasource.TEAM_LOGO_PATHS = {"KC": "data/logos/KC.png", "BUF": "data/logos/BUF.png"}
    mock_get_datasource.return_value = mock_datasource

    # Set up state with code that uses these globals
    mock_state.visualization_code = """
def generate_plot(df):
    import plotly.express as px
    # Access the global variables
    colors = TEAM_COLORS
    logos = TEAM_LOGO_PATHS
    encoder = encode_team_logo
    fig = px.bar(df, x='col1', y='col2')
    return fig
"""

    # Execute
    result_state = execute_visualization_node(mock_state)

    # Verify the visualization was created (meaning globals were accessible)
    assert result_state.visualization is not None
    assert isinstance(result_state.visualization, dict)


@patch("sportsagent.nodes.visualization.visualizationnode.get_datasource")
def test_execute_visualization_with_team_colors_in_code(mock_get_datasource, mock_state):
    """Test that generated code can actually use TEAM_COLORS dictionary."""
    mock_datasource = MagicMock()
    mock_datasource.TEAM_COLORS = {"KC": ["#E31837", "#FFB612"]}
    mock_datasource.TEAM_LOGO_PATHS = {"KC": "data/logos/KC.png"}
    mock_get_datasource.return_value = mock_datasource

    # Code that uses TEAM_COLORS
    mock_state.visualization_code = """
def generate_plot(df):
    import plotly.express as px
    # Use first color from each team
    color_map = {k: v[0] for k, v in TEAM_COLORS.items()}
    fig = px.bar(df, x='col1', y='col2')
    return fig
"""

    result_state = execute_visualization_node(mock_state)

    assert result_state.visualization is not None
