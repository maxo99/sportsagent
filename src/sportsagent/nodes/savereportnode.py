import os
from datetime import datetime

import plotly.io as pio

from sportsagent.config import settings, setup_logging
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.utils import plotly_from_dict

logger = setup_logging(__name__)


def save_report_node(state: ChatbotState) -> ChatbotState:
    """
    Node that saves the report if the user approved it.
    """
    if state.skip_save:
        logger.info("User skipped saving the report.")
        return state

    # Create report directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Simple slug from query (first 20 chars, safe chars only)
    slug = (
        "".join(c for c in state.user_query[:20] if c.isalnum() or c in (" ", "_", "-"))
        .strip()
        .replace(" ", "_")
    )
    report_dir_name = f"report_{timestamp}_{slug}"
    report_dir = os.path.join("data", "outputs", report_dir_name)

    try:
        os.makedirs(report_dir, exist_ok=True)
        logger.info(f"Created report directory: {report_dir}")

        # Save Chart if exists
        chart_filename = None
        if state.visualization:
            try:
                if isinstance(state.visualization, dict):
                    fig = plotly_from_dict(state.visualization)
                else:
                    fig = state.visualization

                # Save as JSON
                pio.write_json(fig, os.path.join(report_dir, "chart.json"))
                # Save as HTML
                if settings.SAVE_HTML:
                    pio.write_html(fig, os.path.join(report_dir, "chart.html"))
                try:
                    pio.write_image(fig, os.path.join(report_dir, "chart.png"))
                except Exception as e:
                    logger.warning(f"Failed to save PNG (kaleido might be missing): {e}")

                chart_filename = "chart.html"
                logger.info("Saved visualization files.")
            except Exception as e:
                logger.error(f"Failed to save visualization: {e}")

        # Prepare Report Content
        report_content = []
        report_content.append(f"# Report: {state.user_query}\n")
        report_content.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        report_content.append("## Query")
        report_content.append(f"```text\n{state.user_query}\n```\n")

        report_content.append("## Response")
        report_content.append(f"{state.generated_response}\n")

        if chart_filename:
            report_content.append("## Visualization")
            if settings.SAVE_HTML:
                report_content.append(f"Interactive chart: [{chart_filename}]({chart_filename})\n")
            report_content.append("![Chart](chart.png)\n")

        if state.visualization_code:
            report_content.append("## Visualization Code")
            report_content.append(f"```python\n{state.visualization_code}\n```\n")

        report_content.append("## Chat History")
        for msg in state.messages:
            role = msg.type if hasattr(msg, "type") else "unknown"
            # Try to handle different message types or dicts if messages are dicts
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
            else:
                role = msg.type
                content = msg.content

            report_content.append(f"### {role.capitalize()}")
            report_content.append(f"{content}\n")

        # Save Report Markdown
        with open(os.path.join(report_dir, "report.md"), "w") as f:
            f.write("\n".join(report_content))

        logger.info(f"Saved report.md to {report_dir}")

    except Exception as e:
        logger.error(f"Failed to save report: {e}")

    return state
