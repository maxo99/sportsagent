import json
import uuid

import pandas as pd
import streamlit as st

from sportsagent.config import settings, setup_logging
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.parsedquery import ParsedQuery
from sportsagent.utils.visualization_helpers import plotly_from_dict
from sportsagent.workflow import compile_workflow

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

if "retrieved_data" not in st.session_state:
    st.session_state["retrieved_data"] = None

# Sidebar
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    # background-color: #f0f2f6; # Optional: change background
    font-size: 12px !important; # Adjust the base font size for sidebar
}
/* Style for specific elements like selectbox labels */
div[data-testid="stSidebar"] label {
    font-size: 10px !important;
}
</style>
""", unsafe_allow_html=True)
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
    # Add metadata for tracing/debugging
    config["metadata"] = {
        "source": "streamlit",
        "session_id": st.session_state["session_id"],
    }

    # If inputs is None, we are resuming
    if inputs is None:
        config["run_name"] = "Resume Workflow (Save Report)"
        stream = graph.stream(None, config=config, stream_mode="updates")
    else:
        config["run_name"] = "Start Workflow"
        st.session_state["workflow_trace"] = []  # Clear trace for new query
        stream = graph.stream(inputs, config=config, stream_mode="updates")

    for chunk in stream:
        for node_name, node_state in chunk.items():
            logger.info(f"Executed node: {node_name}")
            # Update sidebar trace
            st.session_state["workflow_trace"].append(node_name)
            if "internal_trace" in node_state and node_state["internal_trace"]:
                for trace_item in node_state["internal_trace"]:
                    st.session_state["workflow_trace"].append(f"  {trace_item}")

    # Graph.stream yields updates, so we fetch the full state at the end.

    snapshot = graph.get_state(config)
    result = snapshot.values

    # Update sidebar data from snapshot
    if snapshot.values and "retrieved_data" in snapshot.values:
        data = snapshot.values["retrieved_data"]
        if data:
            st.session_state["retrieved_data"] = data

    if snapshot.next:
        if "generate_visualization" in snapshot.next:
            st.session_state["interrupt_state"] = "generate_visualization"
            st.rerun()
        elif "execute_visualization" in snapshot.next:
            st.session_state["interrupt_state"] = "execute_visualization"
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
            st.session_state["retrieved_data"] = data

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


def load_reports():
    """Loads list of available reports."""
    reports_dir = settings.ASSET_OUTPUT_DIR
    if not reports_dir.exists():
        return []

    reports = []
    for entry in reports_dir.iterdir():
        if entry.is_dir() and entry.name.startswith("report_"):
            reports.append(entry.name)

    reports.sort(reverse=True)
    return reports


def display_report(report_dir_name):
    """Displays the content of a selected report."""
    report_path = settings.ASSET_OUTPUT_DIR / report_dir_name

    md_path = report_path / "report.md"
    if md_path.exists():
        with open(md_path) as f:
            content = f.read()
        st.markdown(content)
    else:
        st.warning("No report.md found in this directory.")

    chart_json_path = report_path / "chart.json"
    chart_png_path = report_path / "chart.png"

    if chart_json_path.exists():
        try:
            with open(chart_json_path) as f:
                fig_dict = json.load(f)
            fig = plotly_from_dict(fig_dict)
            st.plotly_chart(fig)
        except Exception as e:
            st.error(f"Error loading interactive chart: {e}")
    elif chart_png_path.exists():
        st.image(chart_png_path, caption="Chart")


# Compile graph
@st.cache_resource
def get_graph():
    return compile_workflow(langgraph_platform=False)


graph = get_graph()

# =============================================================================
# MAIN UI
# =============================================================================

# Tabs
tab_chat, tab_review = st.tabs(["Chat", "Review Reports"])

with tab_chat:
    display_chat_history()

    # Handle Interrupts
    if st.session_state.get("interrupt_state") == "generate_visualization":
        with st.chat_message("assistant"):
            st.write("I can generate a visualization for this. Do you want me to proceed?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, generate chart"):
                    st.session_state["interrupt_state"] = None
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": "User approved chart generation."}
                    )
                    with st.spinner("Generating visualization code..."):
                        run_workflow(None)  # Resume
            with col2:
                if st.button("No, skip"):
                    st.session_state["interrupt_state"] = None
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": "User skipped chart generation."}
                    )
                    config = st.session_state["workflow_config"]
                    graph.update_state(config, {"needs_visualization": False})
                    run_workflow(None)

    elif st.session_state.get("interrupt_state") == "execute_visualization":
        # Get the generated code from state
        config = st.session_state["workflow_config"]
        snapshot = graph.get_state(config)
        code = snapshot.values.get("visualization_code", "")

        with st.chat_message("assistant"):
            st.write("Here is the code I generated to create the chart. Please review it:")
            st.code(code, language="python")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Execute Code"):
                    st.session_state["interrupt_state"] = None
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": "User approved chart execution."}
                    )
                    with st.spinner("Executing visualization..."):
                        run_workflow(None)
            with col2:
                if st.button("Cancel"):
                    st.session_state["interrupt_state"] = None
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": "User cancelled chart execution."}
                    )
                    # Skip execution by updating state
                    graph.update_state(config, {"visualization_code": None})
                    run_workflow(None)

    elif st.session_state.get("interrupt_state") == "approval":
        query = st.session_state.get("approval_query", "unknown")
        with st.chat_message("assistant"):
            st.write(f"I need to fetch more data for: '{query}'. Do you approve?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, fetch data"):
                    st.session_state["interrupt_state"] = None
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": "User approved data retrieval."}
                    )
                    config = st.session_state["workflow_config"]
                    graph.update_state(config, {"approval_result": "approved"})
                    with st.spinner(f"Fetching data for {query}..."):
                        run_workflow(None)
            with col2:
                if st.button("No, stop"):
                    st.session_state["interrupt_state"] = None
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": "User denied data retrieval."}
                    )
                    config = st.session_state["workflow_config"]
                    graph.update_state(config, {"approval_result": "denied"})
                    run_workflow(None)

    elif st.session_state.get("interrupt_state") == "save_report":
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
                        st.session_state["messages"].append(
                            {"role": "assistant", "content": "User approved saving the report."}
                        )
                        with st.spinner("Saving report..."):
                            run_workflow(None)
                with col2:
                    if st.button("No, Skip"):
                        st.session_state["interrupt_state"] = None
                        st.session_state["messages"].append(
                            {"role": "assistant", "content": "User skipped saving the report."}
                        )
                        config = st.session_state["workflow_config"]
                        graph.update_state(config, {"skip_save": True})
                        run_workflow(None)

    # Chat Input
    if prompt := st.chat_input("Ask me about NFL stats..."):
        st.session_state["messages"].append({"role": "user", "content": prompt})

        # Sanitize conversation history for state (remove non-serializable elements like Plotly figures)
        sanitized_history = []
        for msg in st.session_state["messages"]:
            clean_msg = msg.copy()
            if "elements" in clean_msg:
                del clean_msg["elements"]
            sanitized_history.append(clean_msg)

        initial_state = ChatbotState(
            session_id=st.session_state["session_id"],
            user_query=prompt,
            generated_response="",
            conversation_history=sanitized_history,
            retrieved_data=st.session_state["retrieved_data"],
            parsed_query=ParsedQuery(parse_status="unparsed"),
        )

        with st.spinner("Thinking..."):
            run_workflow(initial_state)

with tab_review:
    st.header("Review Saved Reports")
    reports = load_reports()
    if reports:
        selected_report = st.selectbox("Select a report", reports)
        if selected_report:
            st.divider()
            display_report(selected_report)
    else:
        st.info("No reports found.")

# Debug / Data View
if st.session_state.get("retrieved_data"):
    with st.expander("Current Data", expanded=False):
        data = st.session_state["retrieved_data"]
        if data:
            # If it's a dict of datasets, use tabs
            tabs = st.tabs(list(data.keys()))
            for i, (key, records) in enumerate(data.items()):
                with tabs[i]:
                    st.subheader(f"Dataset: {key}")
                    st.dataframe(pd.DataFrame(records))
