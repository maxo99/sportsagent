import logging
from collections.abc import Callable
from typing import Any

import pytest

from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.runner import RunResult

logger = logging.getLogger(__name__)


@pytest.fixture
def make_chat_state() -> Callable[..., ChatbotState]:
    def _make_chat_state(
        generated_response: str = "response",
        visualization: Any | None = None,
        skip_save: bool = False,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> ChatbotState:
        return ChatbotState(
            session_id="session",
            user_query="user prompt",
            generated_response=generated_response,
            conversation_history=conversation_history or [],
            visualization=visualization,
            skip_save=skip_save,
        )

    return _make_chat_state


@pytest.fixture
def make_run_result(make_chat_state: Callable[..., ChatbotState]) -> Callable[..., RunResult]:
    def _make_run_result(
        state: ChatbotState | None = None,
        pending: list[str] | None = None,
    ) -> RunResult:
        return RunResult(state=state or make_chat_state(), pending=pending or [])

    return _make_run_result


@pytest.fixture
def fake_runner_factory(
    make_run_result: Callable[..., RunResult],
) -> Callable[[list[RunResult]], type]:
    def _factory(responses: list[RunResult]) -> type:
        class FakeRunner:
            instances: list["FakeRunner"] = []

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.run_calls: list[tuple[str, list[dict[str, Any]] | None, Any | None]] = []
                self.resume_calls: list[str] = []
                self._responses = responses
                self._index = 0
                FakeRunner.instances.append(self)

            def _next_response(self) -> RunResult:
                if not self._responses:
                    return make_run_result()
                if self._index >= len(self._responses):
                    return self._responses[-1]
                response = self._responses[self._index]
                self._index += 1
                return response

            def run(
                self,
                user_query: str,
                conversation_history: list[dict[str, Any]] | None = None,
                retrieved_data: Any | None = None,
            ) -> RunResult:
                self.run_calls.append((user_query, conversation_history, retrieved_data))
                return self._next_response()

            def resume_with_approval(self, decision: str) -> RunResult:
                self.resume_calls.append(decision)
                return self._next_response()

        return FakeRunner

    return _factory
