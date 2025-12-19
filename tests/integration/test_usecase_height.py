import os

import pandas as pd
import pytest

from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.nodes.queryparser.queryparsernode import query_parser_node
from sportsagent.nodes.retriever.retrievernode import retriever_node


def _enabled() -> bool:
    return os.environ.get("RUN_LIVE_LLM_TESTS", "0") == "1" and bool(
        os.environ.get("OPENAI_API_KEY")
    )


pytestmark = pytest.mark.skipif(
    not _enabled(),
    reason="Live LLM tests are disabled. Set RUN_LIVE_LLM_TESTS=1 and OPENAI_API_KEY.",
)


def test_height_usecase_full_flow() -> None:
    # 1. Parsing
    state = ChatbotState(
        session_id="test_height",
        user_query="Plot QB passing yards by height for 2023",
        generated_response="",
        retrieved_data=None,
    )

    state = query_parser_node(state)
    assert state.error is None
    pq = state.parsed_query
    assert pq.parse_status == "parsed"
    assert "player_info" in pq.enrichment_datasets

    # Check for aggregation
    assert pq.chart_spec.aggregation is not None
    print(f"Inferred Aggregation: {pq.chart_spec.aggregation}")

    # Check for join keys - LLM should follow the updated parsing prompt
    assert any("player_id" in k and "gsis_id" in k for k in pq.enrichment_options.join_keys)

    # 2. Retrieval
    state = retriever_node(state)
    assert state.error is None
    assert state.retrieved_data is not None

    # Check if 'height' column exists in players (successfully merged)
    df = pd.DataFrame(state.retrieved_data.players)

    print(f"Columns in merged players: {list(df.columns)}")

    assert "height" in df.columns
    assert "passing_yards" in df.columns

    # Check some data points
    qbs_with_height = df[df["height"].notna()]
    assert len(qbs_with_height) > 0
    print(f"Found {len(qbs_with_height)} QBs with height information.")

    # SIMULATE THE AGGREGATION AND SORTING THAT WOULD HAPPEN IN THE VIZ NODE
    from sportsagent.nodes.retriever.retrievernode import aggregate_data

    aggregated_df = aggregate_data(df, pq.chart_spec)

    # If x_axis is numeric (height), sort by it
    sorted_df = aggregated_df.sort_values(pq.chart_spec.x_axis, ascending=False)

    print("Sorted and Aggregated Data (Individual QBs by height):")
    # We expect 'player_name' to be in the columns because it was used in group_by
    display_cols = [pq.chart_spec.x_axis, pq.chart_spec.y_axis]
    if "player_name" in sorted_df.columns:
        display_cols.insert(0, "player_name")

    print(sorted_df[display_cols].head(10))

    # Ensure it's sorted by height descending
    assert sorted_df[pq.chart_spec.x_axis].iloc[0] >= sorted_df[pq.chart_spec.x_axis].iloc[1]

    # Ensure we haven't collapsed everything (we should have many rows for different players)
    assert len(sorted_df) > 10
