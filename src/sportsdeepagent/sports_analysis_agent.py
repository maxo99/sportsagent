# from deepagents import create_deep_agent
# from deepagents.backends import StoreBackend
# from langgraph.checkpoint.memory import MemorySaver
# from langgraph.graph.state import CompiledStateGraph
# from langgraph.store.memory import InMemoryStore

# from sportsagent.config import settings
# from sportsagent.tools.dataframe import describe_dataset
# from sportsagent.tools.nfl import get_player_news, get_player_stats

# # from sportsagent.middleware.memory import MemoryInjectionMiddleware
# from sportsagent.workflows.deepagents.middleware.ui_push import GenUIMiddleware
# from sportsagent.workflows.deepagents.prompts.system import (
#     ANALYZER_AGENT_INSTRUCTIONS,
#     RETRIEVAL_AGENT_INSTRUCTIONS,
#     WORKFLOW_INSTRUCTIONS,
# )
# from sportsagent.workflows.deepagents.schemas.sports_analysis_state import SportsAnalysisState

# TOOLS = {
#     "get_player_stats": get_player_stats,
#     "get_player_news": get_player_news,
#     "describe_dataset": describe_dataset,
# }

# INTERRUPTS = {
#     "get_player_stats": {
#         "allowed_decisions": ["approve", "reject"],
#         "description": "I have retrieved player data. 'approve' to send as-is, or 'reject' to cancel and end the workflow.",
#     },
# }


# def create_sportsanalysis_assistant(
#     langgraph_platform=False,
#     **kwargs,
# ) -> CompiledStateGraph:
#     """Create and configure the sports analysis assistant agent.

#     Args:
#         for_deployment: If True, don't pass store/checkpointer (for LangGraph deployment). If False, create InMemoryStore and MemorySaver for local testing.

#     Returns:
#         CompiledStateGraph: Configured SportsAnalysis assistant agent
#     """

#     store = InMemoryStore()

#     # Local testing mode - create and use our own store and checkpointer
#     if not langgraph_platform:
#         kwargs.update(
#             store=store,
#             checkpointer=MemorySaver(),
#         )

#     # Create middleware instances
#     # memory_injection = MemoryInjectionMiddleware(store=store)
#     # post_interrupt_memory = PostInterruptMemoryMiddleware(store=store)

#     genui = GenUIMiddleware(
#         tool_to_genui_map={
#             "get_player_stats": {
#                 "component_name": "get_player_stats",
#             },
#         }
#     )

#     # Build system prompt with default user profile
#     # Note: Memory-based profile can be accessed via the store in middleware
#     # tools_prompt = "\n".join([f"- {tool.name}: {tool.description}" for tool in TOOLS])
#     system_prompt = WORKFLOW_INSTRUCTIONS.format(
#         # tools_prompt=tools_prompt,
#         # user_profile=default_user_profile,
#     )

#     retrieval_sub_agent = {
#         "name": "RetrievalAgent",
#         "description": "Delegate retrieval to the sub-agent RetrievalAgent.",
#         "system_prompt": RETRIEVAL_AGENT_INSTRUCTIONS,
#         "tools": [get_player_stats, get_player_news],
#     }
#     analyzer_sub_agent = {
#         "name": "AnalyzerAgent",
#         "description": "Delegate retrieval to the sub-agent RetrievalAgent.",
#         "system_prompt": ANALYZER_AGENT_INSTRUCTIONS,
#         "tools": [describe_dataset],
#     }

#     # Create agent with deepagents library
#     agent = create_deep_agent(
#         model=settings.LLM_MODEL,
#         tools=[get_player_stats, get_player_news, describe_dataset],
#         middleware=[genui],
#         backend=lambda rt: StoreBackend(rt),
#         context_schema=SportsAnalysisState,
#         system_prompt=system_prompt,
#         interrupt_on=INTERRUPTS,  # type: ignore
#         subagents=[retrieval_sub_agent, analyzer_sub_agent],  # type: ignore
#         **kwargs,
#     )

#     return agent
