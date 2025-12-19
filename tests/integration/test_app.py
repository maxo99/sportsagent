import pytest
from streamlit.testing.v1 import AppTest

from sportsagent.config import settings


@pytest.fixture(scope="session")
def at():
    _at = AppTest.from_file(settings.SRC_DIR / "sportsagent" / "main_st.py", default_timeout=30).run(timeout=60)
    yield _at
    print("Test session completed, cleaning up...")


def test_app_running(at):
    """Test that the app runs without exceptions and displays the correct title."""
    assert not at.exception
    assert at.title[0].value == "🏈 Sports Agent (LangGraph)"


def test_sidebar_debug_info(at):
    """Test that the sidebar displays session ID and debug headers."""
    assert at.sidebar.header[0].value == "Debug Info"
    assert "Session ID:" in at.sidebar.markdown[0].value
    assert at.sidebar.subheader[0].value == "Workflow Trace"


def test_chat_input_updates_state(at):
    """Test that entering a query adds it to the chat history and session state."""
    query = "Show me Josh Allen passing yards 2024"
    at.chat_input[0].set_value(query).run()

    assert not at.exception
    # Check that the message was added to session state
    messages = at.session_state["messages"]
    assert len(messages) > 0
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == query


def test_approval_interrupt_ui(at):
    """Test that the approval interrupt displays the correct buttons and handles clicks."""
    at.session_state["interrupt_state"] = "approval"
    at.session_state["approval_query"] = "Josh Allen stats"
    at.run()

    assert not at.exception
    assert any("I need to fetch more data for: 'Josh Allen stats'" in m.value for m in at.markdown)

    # Check for buttons
    # Note: indices might change if other buttons are added, but usually they are sequential
    yes_button = next(b for b in at.button if b.label == "Yes, fetch data")
    no_button = next(b for b in at.button if b.label == "No, stop")
    assert yes_button
    assert no_button
    # Click "No, stop" to see if it updates state
    no_button.click().run()
    assert at.session_state["interrupt_state"] is None
    assert any(msg["content"] == "User denied data retrieval." for msg in at.session_state["messages"])


def test_review_reports_tab_ui(at):
    """Test that the Review Reports tab header is present."""
    assert any(h.value == "Review Saved Reports" for h in at.header)


def test_visualization_interrupt_ui(at):
    """Test that the visualization interrupt displays the correct buttons."""
    at.session_state["interrupt_state"] = "generate_visualization"
    at.run()

    assert not at.exception
    assert any("I can generate a visualization for this" in m.value for m in at.markdown)

    yes_button = next(b for b in at.button if b.label == "Yes, generate chart")
    no_button = next(b for b in at.button if b.label == "No, skip")

    assert yes_button
    assert no_button
