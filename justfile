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
	uv run uvicorn sportsagent.api:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000}

validate-cli:
	uv run sportsagent chat "Show top 3 QBs by passing yards 2024" --auto-approve --save-assets-to-file

validate-container:
	docker build -t sportsagent . && docker run -v $(pwd)/data/outputs:/app/data/outputs sportsagent chat "Compare Mahomes vs Allen" --auto-approve