# SportsAgent: Autonomous NFL Stats Visualization with LangGraph

**SportsAgent** is an advanced autonomous agent designed to analyze NFL player statistics, perform comparative evaluations, and generate interactive visualizations on demand. Built with **LangGraph**, it demonstrates a robust **Human-in-the-Loop (HITL)** architecture where the agent autonomously plans analysis steps but defers to the user for critical decisions like data fetching and visualization generation.

## High-Level Overview

The system operates as a cyclic graph that alternates between **Retrieval** (fetching data from `nflreadpy`) and **Analysis** (interpreting data with an LLM). It features:

- **Autonomous Reasoning**: The `AnalyzerAgent` determines if the retrieved data is sufficient or if more is needed.
- **Interactive Visualization**: Users can request charts, which are generated on-the-fly by the agent writing and executing Plotly code.
- **Stateful Conversations**: Maintains context across multiple turns, allowing for iterative refinement of queries (e.g., "Compare Mahomes and Allen" -> "Now add Burrow").

## Architecture & Design

The core of SportsAgent is a **LangGraph** workflow that orchestrates the interaction between the user, the LLM, and the data tools.

### LangGraph Workflow

The workflow is defined in `src/sportsagent/workflows/graphs/playereval/workflow.py` and consists of the following key nodes:

1. **Query Parser**: Structured intent extraction to understand which players, positions, and stats are requested.
2. **Retriever**: Fetches raw play-by-play or season-level data using `nflreadpy`.
3. **Analyzer**: A ReAct agent that computes statistics, generates insights, and decides the next step.
4. **Approval Node (HITL)**: A safeguard that pauses execution to ask for user permission before fetching large datasets or performing expensive operations.
5. **Visualization Node (HITL)**: A dedicated step where the agent proposes a visualization, and upon user approval, generates the rendering code.

### Human-in-the-Loop (HITL) Patterns

This project showcases two distinct HITL patterns:

- **Active Approval**: The workflow explicitly pauses at the `approval_node` when the agent signals a need for more data (`request_more_data` tool). This prevents infinite retrieval loops and gives the user cost control.
- **Opt-In Visualization**: The `visualization_node` is conditional. The agent sets a `needs_visualization` flag, but the actual generation only occurs after the user confirms via the UI.

### State Management

Managing state in a complex agentic workflow is critical. We use a custom Pydantic model `ChatbotState` that tracks:

- **`retrieved_data`**: A canonical list of dictionaries containing the raw NFL data. To ensure compatibility with LangGraph's checkpointing (which uses `msgpack`), we avoid storing raw Pandas DataFrames directly in the state.
- **`visualization`**: Stores the generated Plotly figure as a JSON-serialized dictionary, allowing it to be passed between nodes and rendered by the frontend without pickling issues.

## Key Components

### Analyzer Agent

ReAct agent which analyzes the data for statistical relevance, performs comparisons, and decides when to request more data or generate visualizations.

### Visualization Engine

Translates data, preloaded assets, and user intent into high-quality Plotly charts. It receives a schema of the data and the user's query, then writes Python code to generate the figure, which is executed in a sandboxed environment.

### Streamlit UI

The application frontend is built with Streamlit to provide a rich, interactive experience. It features:

- **Workflow Tracing**: A sidebar that visualizes the active path through the LangGraph nodes.
- **Interactive Charts**: Renders the Plotly JSON artifacts directly.
- **Data Inspection**: Allows users to view the raw data tables used by the agent.

## Tech Stack

- **Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/)
- **Data Source**: [nflreadpy](https://github.com/nflverse/nflreadpy)
- **Frontend**: Streamlit
- **Visualization**: Plotly

## Diagram

```mermaid
---
config:
  flowchart:
    curve: stepAfter
fontFamily: Arial
look: handDrawn
theme: neutral
---
graph TD;
 __start__([<p>__start__</p>]):::first
 entry(entry)
 exit(exit)
 query_parser(query_parser)
 retriever(retriever)
 AnalyzerReactAgent(AnalyzerReactAgent)
 generate_visualization(generate_visualization<hr/><small><em>__interrupt = before</em></small>):::hitl
 execute_visualization(execute_visualization<hr/><small><em>__interrupt = before</em></small>):::hitl
 save_report(save_report<hr/><small><em>__interrupt = before</em></small>):::hitl
 approval(approval<hr/><small><em>__interrupt = before</em></small>):::hitl
 __end__([<p>__end__</p>]):::last
 AnalyzerReactAgent -.-> approval;
 AnalyzerReactAgent -.-> exit;
 AnalyzerReactAgent -.-> generate_visualization;
 AnalyzerReactAgent -.-> save_report;
 __start__ --> entry;
 approval --> retriever;
 entry -.-> exit;
 entry -.-> query_parser;
 execute_visualization --> save_report;
 generate_visualization --> execute_visualization;
 query_parser -.-> exit;
 query_parser -.-> retriever;
 retriever -.-> AnalyzerReactAgent;
 retriever -.-> exit;
 save_report --> exit;
 exit --> __end__;
 classDef default fill:#E1F5FE,stroke:#01579B,stroke-width:2px,color:#000000,line-height:1.2
 classDef first fill:#D1C4E9,stroke-dasharray: 5 5,color:#000000
 classDef last fill:#D1C4E9,stroke:#4A148C,stroke-width:2px,color:#000000

 classDef hitl fill:#FFF3E0,stroke:#E65100,stroke-width:2px,color:#000000

    subgraph Legend
        direction LR
        L1(System Step):::default
        L2(Start / End):::first
        L3(Human Action):::hitl
    end

```

<!-- REPORTS-START -->
## Generated Reports

- [20251211-181552: RB receivingyards-rushingyards 2023](data/outputs/20251211_181552_RB_receivingyards-rushingyards_2023/report.md)
- [20251210-184118: QB passingyards 2024](data/outputs/20251210_184118_QB_passingyards_2024/report.md)
- [20251209-091723: QB passingyards 2025](data/outputs/20251209_091723_QB_passingyards_2025/report.md)
- [20251209-073659: rushingyards 2024](data/outputs/20251209_073659_rushingyards_2024/report.md)
- [20251209-065240: QB sackyards 2025](data/outputs/20251209_065240_QB_sackyards_2025/report.md)
- [20251208-191436: RBs rushyardsavg 2025](data/outputs/20251208_191436_RBs_rushyardsavg_2025/report.md)
<!-- REPORTS-END -->