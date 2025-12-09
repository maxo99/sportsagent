import uuid
import pandas as pd
import streamlit as st

from sportsagent.config import setup_logging
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.workflow import graph
from sportsagent.utils import plotly_from_dict

logger = setup_logging(__name__)

# =============================================================================
# STREAMLIT APP SETUP
# =============================================================================

TITLE = "Sports Agent (LangGraph)"
st.set_page_config(page_title=TITLE, page_icon="🏈")
st.title("🏈 " + TITLE)

# Initialize Session State
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

if "workflow_config" not in st.session_state:
    st.session_state["workflow_config"] = {
        "configurable": {"thread_id": st.session_state["session_id"]}
    }

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "workflow_trace" not in st.session_state:
    st.session_state["workflow_trace"] = []

# Sidebar
st.sidebar.header("Debug Info")
st.sidebar.write(f"Session ID: {st.session_state['session_id']}")

st.sidebar.subheader("Workflow Trace")
for step in st.session_state["workflow_trace"]:
    st.sidebar.text(f"→ {step}")


# =============================================================================
# HELPERS
# =============================================================================


def display_chat_history():
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "elements" in msg:
                for element in msg["elements"]:
                    if element["type"] == "plotly":
                        st.plotly_chart(element["data"])


def run_workflow(inputs=None):
    """Runs the workflow, handling interrupts for visualization and approval."""

    config = st.session_state["workflow_config"]

    # If inputs is None, we are resuming
    if inputs is None:
        logger.info("Resuming workflow...")
        # Clear trace on new run if not resuming? No, keep history or clear?
        # Let's append to existing trace for the session
        stream = graph.stream(None, config=config, stream_mode="updates")
    else:
        logger.info("Starting workflow...")
        st.session_state["workflow_trace"] = []  # Clear trace for new query
        stream = graph.stream(inputs, config=config, stream_mode="updates")

    final_state = None
    for chunk in stream:
        for node_name, node_state in chunk.items():
            logger.info(f"Executed node: {node_name}")
            st.session_state["workflow_trace"].append(node_name)
            # Force sidebar update? st.rerun() might be too aggressive here.
            # We can use a placeholder if we want real-time updates, but sidebar is tricky.
            # For now, just appending to state. The sidebar will update on next rerun.
            final_state = node_state  # Keep track of the latest state

    # If stream finishes, we have the final state in final_state (or we need to get it)
    # Actually, graph.stream yields updates. The last update might not be the full state.
    # It's safer to get the state at the end.

    # Check state after invoke (it might be paused)
    snapshot = graph.get_state(config)
    result = snapshot.values  # This effectively becomes our result/final_state

    # Check state after invoke (it might be paused)
    snapshot = graph.get_state(config)

    # Update sidebar data from snapshot
    if snapshot.values and "retrieved_data" in snapshot.values:
        data = snapshot.values["retrieved_data"]
        if data:
            st.session_state["current_dataframe"] = pd.DataFrame(data)

    if snapshot.next:
        if "visualization" in snapshot.next:
            st.session_state["interrupt_state"] = "visualization"
            st.rerun()
        elif "approval" in snapshot.next:
            st.session_state["interrupt_state"] = "approval"
            st.session_state["approval_query"] = snapshot.values.get("user_query")
            st.rerun()
        elif "save_report" in snapshot.next:
            st.session_state["interrupt_state"] = "save_report"
            st.rerun()
    else:
        # Workflow finished
        st.session_state["interrupt_state"] = None
        # Use the result we captured/derived
        process_final_result(result)


def process_final_result(final_state):
    # Update sidebar data from final state
    if final_state and "retrieved_data" in final_state:
        data = final_state["retrieved_data"]
        if data:
            st.session_state["current_dataframe"] = pd.DataFrame(data)

    response = final_state.get("generated_response", "")
    visualization = final_state.get("visualization")

    elements = []
    if visualization:
        # If it's a dict (from JSON serialization), convert back to figure
        if isinstance(visualization, dict):
            fig = plotly_from_dict(visualization)
            elements.append({"type": "plotly", "data": fig})
        else:
            elements.append({"type": "plotly", "data": visualization})

    st.session_state["messages"].append(
        {"role": "assistant", "content": response, "elements": elements}
    )
    st.rerun()


# =============================================================================
# MAIN UI
# =============================================================================

display_chat_history()

# Handle Interrupts
if st.session_state.get("interrupt_state") == "visualization":
    with st.chat_message("assistant"):
        st.write("I can generate a visualization for this. Do you want me to proceed?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, generate chart"):
                st.session_state["interrupt_state"] = None
                with st.spinner("Generating visualization..."):
                    run_workflow(None)  # Resume
        with col2:
            if st.button("No, skip"):
                st.session_state["interrupt_state"] = None
                # TODO: Handle skip logic (might need a way to inject a "skip" signal or just break)
                # For now, we just resume and let the node handle it (or we might need to update state)
                # In main_cl.py we just break. Here we probably want to just resume but maybe set needs_visualization=False?
                # Actually, if we resume without updating state, it will just try to run visualization_node again.
                # We need to update the state to skip visualization.
                config = st.session_state["workflow_config"]
                graph.update_state(config, {"needs_visualization": False})
                run_workflow(None)

elif st.session_state.get("interrupt_state") == "approval":
    query = st.session_state.get("approval_query", "unknown")
    with st.chat_message("assistant"):
        st.write(f"I need to fetch more data for: '{query}'. Do you approve?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, fetch data"):
                st.session_state["interrupt_state"] = None
                with st.spinner(f"Fetching data for {query}..."):
                    run_workflow(None)
        with col2:
            if st.button("No, stop"):
                st.session_state["interrupt_state"] = None
                st.session_state["messages"].append(
                    {"role": "assistant", "content": "Data retrieval cancelled."}
                )
                st.rerun()

elif st.session_state.get("interrupt_state") == "save_report":
    # Display the result BEFORE asking to save
    # We need to get the current state to show the response/chart
    config = st.session_state["workflow_config"]
    snapshot = graph.get_state(config)
    if snapshot.values:
        response = snapshot.values.get("generated_response", "")
        visualization = snapshot.values.get("visualization")

        with st.chat_message("assistant"):
            st.write(response)
            if visualization:
                if isinstance(visualization, dict):
                    fig = plotly_from_dict(visualization)
                    st.plotly_chart(fig)
                else:
                    st.plotly_chart(visualization)

            st.write("---")
            st.write("**Do you want to save this report?**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Save Report"):
                    st.session_state["interrupt_state"] = None
                    with st.spinner("Saving report..."):
                        run_workflow(None)
            with col2:
                if st.button("No, Skip"):
                    st.session_state["interrupt_state"] = None
                    config = st.session_state["workflow_config"]
                    graph.update_state(config, {"skip_save": True})
                    run_workflow(None)

# Chat Input
if prompt := st.chat_input("Ask me about NFL stats..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})

    initial_state = ChatbotState(
        session_id=st.session_state["session_id"],
        user_query=prompt,
        generated_response="",
        conversation_history=[],  # We could populate this from st.session_state["messages"] if needed
    )

    with st.spinner("Thinking..."):
        run_workflow(initial_state)

# Debug / Data View
if "current_dataframe" in st.session_state:
    with st.expander("Current Data", expanded=False):
        st.dataframe(st.session_state["current_dataframe"])
