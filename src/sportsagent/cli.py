import subprocess
import sys


def start_app():
    """Run the Streamlit app."""
    subprocess.run(["streamlit", "run", "src/sportsagent/main_st.py"])


def start_langgraph():
    """Run LangGraph dev."""
    subprocess.run(["langgraph", "dev"])
