from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.memory import InMemoryStore

from sportsagent import routing
from sportsagent.config import setup_logging
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.nodes.analyzer.analyzernode import analyzer_node
from sportsagent.nodes.queryparser.queryparsernode import query_parser_node
from sportsagent.nodes.retriever.retrievernode import retriever_node
from sportsagent.nodes.visualization.visualizationnode import (
    execute_visualization_node,
    generate_visualization_node,
)
from sportsagent.nodes.workflow.entrynode import entry_node
from sportsagent.nodes.workflow.exitnode import exit_node
from sportsagent.nodes.workflow.savereportnode import save_report_node

logger = setup_logging(__name__)


NODES = {
    "entry": entry_node,
    "exit": exit_node,
    "query_parser": query_parser_node,
    "retriever": retriever_node,
    "AnalyzerReactAgent": analyzer_node,
    "generate_visualization": generate_visualization_node,
    "execute_visualization": execute_visualization_node,
    "save_report": save_report_node,
}

CONDITIONAL_EDGES = [
    (
        "entry",
        routing.should_continue_after_entry,
        ["query_parser", "exit"],
    ),
    (
        "query_parser",
        routing.should_continue_after_parser,
        ["retriever", "generate_visualization", "exit"],
    ),
    (
        "retriever",
        routing.should_continue_after_retriever,
        ["AnalyzerReactAgent", "exit"],
    ),
    (
        "AnalyzerReactAgent",
        routing.should_continue_after_analyzer,
        ["generate_visualization", "save_report", "exit"],
    ),
]


def create_workflow() -> StateGraph:
    logger.info("Creating LangGraph workflow")

    workflow = StateGraph(ChatbotState)

    for name, node in NODES.items():
        logger.info(f"Adding node: {name}")
        workflow.add_node(name, node)

    workflow.set_entry_point("entry")

    for source, condition_func, targets in CONDITIONAL_EDGES:
        logger.info(f"Adding conditional edge from {source} to {targets}")
        workflow.add_conditional_edges(source, condition_func, targets)

    workflow.add_edge("generate_visualization", "execute_visualization")
    workflow.add_edge("execute_visualization", "save_report")
    workflow.add_edge("save_report", "exit")
    workflow.add_edge("exit", END)

    logger.info("LangGraph workflow created successfully")
    return workflow


def compile_workflow(
    langgraph_platform=False,
    **kwargs,
) -> CompiledStateGraph:
    """Create and configure the sports analysis assistant agent.

    Args:
        for_deployment: If True, don't pass store/checkpointer (for LangGraph deployment). If False, create InMemoryStore and MemorySaver for local testing.

    Returns:
        CompiledStateGraph: Configured SportsAnalysis assistant agent
    """

    if not langgraph_platform:
        # Local testing mode - create and use our own store and checkpointer
        store = InMemoryStore()
        checkpointer = MemorySaver()
        kwargs.update(
            store=store,
            checkpointer=checkpointer,
        )
        # set_analyzeragent(checkpointer=checkpointer, store=store)
    workflow = create_workflow()

    compiled = workflow.compile(
        interrupt_before=[
            "generate_visualization",
            "execute_visualization",
            "save_report",
        ],
        **kwargs,
    )
    logger.info("LangGraph workflow compiled successfully")
    return compiled
