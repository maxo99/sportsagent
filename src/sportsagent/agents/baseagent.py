from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

from sportsagent import settings


class BaseAgent:
    _compiled_graph: CompiledStateGraph
    response = None

    def __init__(self, **kwargs) -> None:
        self._compiled_graph = self.create(**kwargs)

    def create(
        self,
        recursion_limit: int = 5,
        **kwargs,
    ) -> CompiledStateGraph:
        agent = create_agent(
            model=settings.LLM_MODEL,
            tools=self.tools,
            system_prompt=SystemMessage(content=self.systemMessage),
            checkpointer=InMemorySaver() if settings.ENABLE_CHECKPOINTING else None,
            **kwargs,
        ).with_config({"recursion_limit": recursion_limit})
        return agent

    @property
    def agentName(self) -> str:
        raise NotImplementedError

    @property
    def systemMessage(self) -> str:
        raise NotImplementedError

    @property
    def tools(self) -> list:
        raise NotImplementedError


def get_tool_call_names(messages):
    """
    Method to extract the tool call names from a list of LangChain messages.

    Parameters:
    ----------
    messages : list
        A list of LangChain messages.

    Returns:
    -------
    tool_calls : list
        A list of tool call names.

    """
    tool_calls = []
    for message in messages:
        try:
            if "tool_call_id" in list(dict(message).keys()):
                tool_calls.append(message.name)
        except Exception:
            pass
    return tool_calls
