import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from sportsagent.config import settings, setup_logging
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.utils import get_prompt_template

logger = setup_logging(__name__)


def visualization_node(state: ChatbotState) -> ChatbotState:
    """
    Node that handles data visualization if requested.
    """
    if not state.needs_visualization:
        return state

    if state.retrieved_data is None or len(state.retrieved_data) == 0:
        logger.warning("Visualization requested but no data available.")
        return state

    logger.info("Generating visualization...")

    try:
        # Prepare data summary
        df = pd.DataFrame(state.retrieved_data)
        # Limit rows for prompt context
        data_summary = (
            f"Columns: {list(df.columns)}\nSample data (first 5 rows):\n{df.head().to_string()}"
        )

        # Initialize LLM
        llm = ChatOpenAI(model=settings.OPENAI_MODEL)

        # Get and render prompt
        template = get_prompt_template("visualization_instruction.j2")
        prompt_text = template.render(query=state.user_query, data_summary=data_summary)

        chain = llm | StrOutputParser()

        # Generate code
        code = chain.invoke(prompt_text)

        # Clean code (remove markdown if present despite instructions)
        code = code.replace("```python", "").replace("```", "").strip()

        logger.info(f"Generated visualization code:\n{code}")

        # Execute code
        local_vars = {}
        try:
            exec(code, {}, local_vars)
            generate_plot = local_vars.get("generate_plot")

            if generate_plot and callable(generate_plot):
                fig = generate_plot(df)
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
        logger.error(f"Visualization failed: {e}")

    return state
