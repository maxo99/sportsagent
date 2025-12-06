

default:
	just --list

run-streamlit:
	uv run streamlit run src/sportsagent/main_st.py

run-chainlit:
	uv run chainlit run src/sportsagent/main_cl.py

run-langgraph:
	uv run langgraph dev