from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langgraph.graph.state import CompiledStateGraph

from sportsagent import settings


class BaseAgent(CompiledStateGraph):
    def create(self) -> CompiledStateGraph:
        agent = create_agent(
            model=settings.LLM_MODEL,
            tools=self.tools,
            system_prompt=SystemMessage(content=self.systemMessage),
        )
        return agent

    @property
    def systemMessage(self) -> str:
        raise NotImplementedError

    @property
    def tools(self) -> list:
        return []
