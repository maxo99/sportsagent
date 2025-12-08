import datetime
import operator
from collections.abc import Sequence
from typing import Annotated, Any

import pandas as pd
from langchain.agents import AgentState
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from sportsagent import utils
from sportsagent.agents.baseagent import BaseAgent, get_tool_call_names
from sportsagent.config import settings, setup_logging
from sportsagent.tools.common import request_more_data
from sportsagent.tools.dataframe import compare_performance, describe_dataset, explain_data

logger = setup_logging(__name__)


class AnalyzerGraphState(AgentState):
    internal_messages: Annotated[Sequence[BaseMessage], operator.add]
    user_instructions: str
    data_raw: dict
    eda_artifacts: dict
    tool_calls: list


class AnalyzerAgent(BaseAgent):
    def create(
        self,
        recursion_limit: int = 5,
        **kwargs,
    ) -> CompiledStateGraph[Any, None, Any, Any]:
        return super().create(
            recursion_limit=recursion_limit,
            state_schema=AnalyzerGraphState,
            **kwargs,
        )

    @property
    def agentName(self) -> str:
        return "analyzer_agent"

    @property
    def systemMessage(self) -> str:
        current_year = datetime.datetime.now().year
        return utils.get_prompt_template("analyzer_system.j2").render(current_year=current_year)

    @property
    def tools(self) -> list:
        return [
            explain_data,
            describe_dataset,
            compare_performance,
            request_more_data,
        ]

    async def ainvoke_agent(
        self,
        user_instructions: str | None = None,
        data_raw: pd.DataFrame | None = None,
        **kwargs,
    ):
        """
        Asynchronously runs the agent with user instructions and data.

        Parameters:
        ----------
        user_instructions : str, optional
            The instructions for the agent.
        data_raw : pd.DataFrame, optional
            The input data as a DataFrame.
        """
        response = await self._compiled_graph.ainvoke(
            {
                "user_instructions": user_instructions,
                "data_raw": data_raw.to_dict() if data_raw is not None else None,
            },
            **kwargs,
        )
        self.response = response
        return None

    def invoke_agent(
        self,
        user_instructions: str | None = None,
        data_raw: pd.DataFrame | None = None,
        session_id: str | None = None,
        **kwargs,
    ):
        """
        Synchronously runs the agent with user instructions and data.

        Parameters:
        ----------
        user_instructions : str, optional
            The instructions for the agent.
        data_raw : pd.DataFrame, optional
            The input data as a DataFrame.
        """

        response = self._compiled_graph.invoke(
            input={
                "messages": [HumanMessage(content=user_instructions)] if user_instructions else [],
                "user_instructions": user_instructions,
                "data_raw": data_raw.to_dict() if data_raw is not None else None,
            },
            config={
                "configurable": {"thread_id": session_id or settings.DEFAULT_SESSION},
            },
            **kwargs,
        )
        self.response = response
        return None

    def get_internal_messages(self, markdown: bool = False):
        """
        Returns internal messages from the agent response.
        """
        messages = self.response.get("internal_messages", [])
        if not messages:
            messages = self.response.get("messages", [])

        # pretty_print = "\n\n".join(
        #     [
        #         f"### {msg.type.upper()}\n\nID: {msg.id}\n\nContent:\n\n{msg.content}"
        #         for msg in messages
        #     ]
        # )
        # if markdown:
        #     return Markdown(pretty_print)
        # else:
        return messages

    def get_artifacts(self, as_dataframe: bool = False):
        """
        Returns the EDA artifacts from the agent response.
        """
        if as_dataframe:
            return pd.DataFrame(self.response["eda_artifacts"])
        else:
            return self.response["eda_artifacts"]

    def get_ai_message(self, markdown: bool = False) -> str:
        """
        Returns the AI message from the agent response.
        """
        messages = self.response.get("messages", [])
        content = messages[-1].content if messages else ""

        # if markdown:
        #     return Markdown(content)
        # else:
        return content

    def get_tool_calls(self):
        """
        Returns the tool calls made by the agent.
        """
        if self.response and "tool_calls" in self.response:
            return self.response["tool_calls"]

        if self.response and "messages" in self.response:
            return get_tool_call_names(self.response["messages"])

        return []
