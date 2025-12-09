from sportsagent.workflow import compile_workflow

# Expose the compiled graph for LangGraph Studio/CLI
graph = compile_workflow(langgraph_platform=True)
