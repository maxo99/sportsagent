default:
	just --list

run-streamlit:
	uv run streamlit run src/sportsagent/main_st.py

run-langgraph:
	uv run langgraph dev

update-readme:
	uv run python scripts/update_readme.py


test:
	uv run pytest --cov=src --cov-report=term-missing tests/unit tests/integration

	
test-all:
	uv run pytest --cov=src --cov-report=term-missing tests/unit tests/integration tests/live

run-api:
	uv run uvicorn sportsagent.api:app --host 0.0.0.0 --port 8000