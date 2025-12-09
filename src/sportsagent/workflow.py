from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from sportsagent import routing
from sportsagent.config import setup_logging
from sportsagent.models.chatbotstate import ChatbotState

# from sportsagent.nodes.memorynode import memory_node
from sportsagent.nodes.analyzernode import analyzer_node
from sportsagent.nodes.approvalnode import approval_node
from sportsagent.nodes.entrynode import entry_node
from sportsagent.nodes.exitnode import exit_node
from sportsagent.nodes.queryparsernode import query_parser_node
from sportsagent.nodes.retrievernode import retriever_node
from sportsagent.nodes.savereportnode import save_report_node
from sportsagent.nodes.visualizationnode import visualization_node

logger = setup_logging(__name__)


NODES = {
    "entry": entry_node,
    "exit": exit_node,
    "query_parser": query_parser_node,
    "retriever": retriever_node,
    "analyzer": analyzer_node,
    "visualization": visualization_node,
    "save_report": save_report_node,
    "approval": approval_node,
    # "memory": memory_node,
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
        ["retriever", "exit"],
    ),
    (
        "retriever",
        routing.should_continue_after_retriever,
        ["analyzer", "exit"],
    ),
    (
        "analyzer",
        routing.should_continue_after_analyzer,
        ["approval", "visualization", "save_report", "exit"],
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

    workflow.add_edge("visualization", "save_report")
    workflow.add_edge("save_report", "exit")
    workflow.add_edge("approval", "retriever")
    workflow.add_edge("exit", END)

    logger.info("LangGraph workflow created successfully")
    return workflow


def compile_workflow():
    workflow = create_workflow()
    checkpointer = MemorySaver()
    compiled = workflow.compile(
        checkpointer=checkpointer, interrupt_before=["visualization", "approval", "save_report"]
    )
    logger.info("LangGraph workflow compiled successfully")
    return compiled


# Expose the compiled graph for LangGraph Studio/CLI
graph = compile_workflow()
