import asyncio

from sportsagent.config import setup_logging
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.nodes.queryparser.queryparsernode import query_parser_node

setup_logging(__name__)


def test_position_lookup():
    print("Testing Position Lookup...")

    # 1. Test Parsing
    state = ChatbotState(
        session_id="test_session",
        user_query="Show me stats for all QBs in week 1 of 2023",
        generated_response="",
    )

    # Mock ChatOpenAI
    from unittest.mock import MagicMock, patch

    from sportsagent.models.parsedquery import ParsedQuery, TimePeriod

    mock_parsed_query = ParsedQuery(
        positions=["QB"], time_period=TimePeriod(season=2023, week=1), query_intent="player_stats"
    )

    with patch("sportsagent.nodes.queryparser.queryparsernode.ChatOpenAI") as MockChatOpenAI:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_parsed_query
        MockChatOpenAI.return_value = mock_llm

        state = query_parser_node(state)

    print(f"Parsed Query: {state.parsed_query}")

    if state.error:
        print(f"Parsing Error: {state.error}")
        print(f"Error Message: {state.generated_response}")
        return

    if state.parsed_query and "QB" in state.parsed_query.positions:
        print("SUCCESS: Position 'QB' extracted correctly.")
    else:
        print("FAILURE: Position 'QB' NOT extracted.")
        return

    # 2. Test Retrieval
    # Mocking retrieval to avoid external calls if needed, but integration test is better here
    # For now, let's try to run it (assuming nflreadpy works)

    try:
        state = asyncio.run(retriever_node_async(state))

        if state.retrieved_data and len(state.retrieved_data) > 0:
            print(f"SUCCESS: Retrieved {len(state.retrieved_data)} records.")
            print(f"Sample: {state.retrieved_data[0]}")
        else:
            print("FAILURE: No data retrieved.")

    except Exception as e:
        print(f"Error during retrieval: {e}")


async def retriever_node_async(state):
    from sportsagent.nodes.retriever.retrievernode import retrieve_data

    return await retrieve_data(state)


if __name__ == "__main__":
    test_position_lookup()
