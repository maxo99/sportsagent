import re

import dotenv
from langchain_core.runnables.graph import CurveStyle, NodeStyles

from sportsagent.workflow import compile_workflow

dotenv.load_dotenv()


graph = compile_workflow()
HITL_NODES = [
    "approval",
    "generate_visualization",
    "execute_visualization",
    "save_report",
]


style_default = "fill:#E1F5FE,stroke:#01579B,stroke-width:2px,color:#000000,line-height:1.2"
style_first = "fill:#D1C4E9,stroke-dasharray: 5 5,color:#000000"
style_last = "fill:#D1C4E9,stroke:#4A148C,stroke-width:2px,color:#000000"
style_hitl = "fill:#FFF3E0,stroke:#E65100,stroke-width:2px,color:#000000"

node_colors = NodeStyles(default=style_default, first=style_first, last=style_last)

# Get the mermaid graph definition
mermaid_text = graph.get_graph(xray=1).draw_mermaid(
    node_colors=node_colors,
    curve_style=CurveStyle.STEP_AFTER,
    frontmatter_config={
        "theme": "neutral",
        "look": "handDrawn",
        "fontFamily": "Arial",
    },
)

# ------------ Add HITL Styling ------------ #


# Manually add the HITL class definition
mermaid_text += f"\n\tclassDef hitl {style_hitl}\n"

# Manually apply the HITL class to the specified nodes
for node in HITL_NODES:
    # Pattern looks for: node_name(node_label)
    pattern = re.compile(rf"(\b{node}\(.*?<hr/>.*?\)|\b{node}\(.*?\))")
    # We want to change it to: node_name(node_label):::hitl
    mermaid_text = pattern.sub(r"\1:::hitl", mermaid_text)

# ------------ Save Results ------------ #

# Write to the mmd file
with open("docs/workflow_diagram.mmd", "w") as f:
    f.write(mermaid_text)

# Update README.md
readme_path = "README.md"
with open(readme_path) as f:
    readme_content = f.read()

new_readme_content = re.sub(
    r"```mermaid\n.*?```", f"```mermaid\n{mermaid_text}\n```", readme_content, flags=re.DOTALL
)

with open(readme_path, "w") as f:
    f.write(new_readme_content)

print("Successfully updated docs/workflow_diagram.mmd and README.md with improved styling.")
