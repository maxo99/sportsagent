default:
	just --list

run-streamlit:
	uv run streamlit run src/sportsagent/main_st.py

run-langgraph:
	uv run langgraph dev

update-readme:
	python scripts/update_readme.py