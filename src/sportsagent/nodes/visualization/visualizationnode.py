import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from sportsagent.config import settings, setup_logging
from sportsagent.datasource import get_datasource
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.nodes.visualization import get_visualization_template
from sportsagent.utils.visualization_helpers import encode_team_logo

logger = setup_logging(__name__)


def generate_visualization_node(state: ChatbotState) -> ChatbotState:
    """
    Node that generates visualization code but does not execute it.
    """
    if not state.needs_visualization:
        return state

    if state.retrieved_data is None or len(state.retrieved_data) == 0:
        logger.warning("Visualization requested but no data available.")
        return state

    logger.info("Generating visualization code...")

    try:
        data_summary = ""
        primary_df = None

        if state.retrieved_data:
            for key, records in state.retrieved_data.items():
                if records:
                    df = pd.DataFrame(records)
                    data_summary += f"\n### Dataset: {key}\nColumns: {list(df.columns)}\nSample data (first 5 rows):\n{df.head().to_string()}\n"
                    if primary_df is None:
                        primary_df = df
        else:
            logger.warning("No retrieved data available for visualization.")
            return state

        # Initialize LLM
        llm = ChatOpenAI(model=settings.OPENAI_MODEL)

        # Validate chart_spec columns exist in data if chart_spec is provided
        chart_spec_dict = None
        if state.parsed_query.chart_spec:
            chart_spec = state.parsed_query.chart_spec
            chart_spec_dict = chart_spec.model_dump()

            # Get available columns from primary dataset
            available_columns = set(primary_df.columns) if primary_df is not None else set()

            # Check if required columns exist
            missing_columns = []
            if chart_spec.x_axis and chart_spec.x_axis not in available_columns:
                missing_columns.append(chart_spec.x_axis)
            if chart_spec.y_axis and chart_spec.y_axis not in available_columns:
                missing_columns.append(chart_spec.y_axis)

            if missing_columns:
                logger.warning(
                    f"Chart spec references missing columns: {missing_columns}. "
                    f"Available columns: {list(available_columns)}"
                )
                # Try to find similar column names (fuzzy matching)
                for missing_col in missing_columns[:]:
                    similar = [
                        col
                        for col in available_columns
                        if missing_col.replace("_", "").lower() in col.replace("_", "").lower()
                    ]
                    if similar:
                        logger.info(f"Found similar column for '{missing_col}': {similar[0]}")
                        # Update chart_spec_dict with corrected column name
                        if chart_spec.x_axis == missing_col:
                            chart_spec_dict["x_axis"] = similar[0]
                        if chart_spec.y_axis == missing_col:
                            chart_spec_dict["y_axis"] = similar[0]

        template = get_visualization_template("visualization_instruction.j2")
        prompt_text = template.render(
            query=state.user_query,
            data_summary=data_summary,
            chart_spec=chart_spec_dict,
        )

        chain = llm | StrOutputParser()

        code = chain.invoke(prompt_text)

        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        if "def generate_plot" in code:
            start_idx = code.find("def generate_plot")
            code = code[start_idx:]

        code = code.strip()

        logger.info(f"Generated visualization code:\n{code}")
        state.visualization_code = code

    except Exception as e:
        logger.error(f"Visualization generation failed: {e}")

    return state


def execute_visualization_node(state: ChatbotState) -> ChatbotState:
    """
    Node that executes the generated visualization code.
    """
    if not state.visualization_code:
        logger.warning("No visualization code to execute.")
        return state

    logger.info("Executing visualization code...")

    try:
        datasets = {}
        primary_df = pd.DataFrame()

        if state.retrieved_data:
            for key, records in state.retrieved_data.items():
                if records:
                    datasets[key] = pd.DataFrame(records)

            if "players" in datasets:
                primary_df = datasets["players"]
            elif "teams" in datasets:
                primary_df = datasets["teams"]
            elif datasets:
                primary_df = list(datasets.values())[0]
        else:
            logger.warning("No retrieved data available for execution.")
            return state

        local_vars = {}
        datasource = get_datasource()
        global_vars = {
            "TEAM_COLORS": datasource.TEAM_COLORS,
            "TEAM_LOGO_PATHS": datasource.TEAM_LOGO_PATHS,
            "encode_team_logo": encode_team_logo,
        }

        try:
            exec(state.visualization_code, global_vars, local_vars)
            generate_plot = local_vars.get("generate_plot")

            if generate_plot and callable(generate_plot):
                fig = generate_plot(primary_df)
                if fig:
                    # Convert to dict for serialization (msgpack compatibility)
                    import json

                    import plotly.io as pio

                    fig_json = pio.to_json(fig)
                    if not fig_json:
                        raise ValueError("Failed to serialize figure to JSON")
                    state.visualization = json.loads(fig_json)
                    logger.info("Visualization generated and serialized successfully.")
                else:
                    logger.warning("Function 'generate_plot' returned None.")
            else:
                logger.warning(
                    "Code executed but function 'generate_plot' not found or not callable."
                )

        except Exception as exec_error:
            logger.error(f"Error executing visualization code: {exec_error}")

    except Exception as e:
        logger.error(f"Visualization execution failed: {e}")

    return state
