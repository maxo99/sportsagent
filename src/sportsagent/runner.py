import uuid
from dataclasses import dataclass
from typing import Any

from langchain_core.runnables import RunnableConfig

from sportsagent.config import setup_logging
from sportsagent.models.chatbotstate import ChatbotState
from sportsagent.models.parsedquery import ParsedQuery
from sportsagent.workflow import compile_workflow

logger = setup_logging(__name__)


@dataclass
class RunResult:
    state: ChatbotState
    pending: list[str]


class WorkflowRunner:
    base_config: RunnableConfig

    def __init__(
        self,
        session_id: str | None = None,
        auto_approve: bool = False,
        save_assets_to_file: bool = False,
    ) -> None:
        try:
            self.session_id = session_id or str(uuid.uuid4())
            self.auto_approve = auto_approve
            self.save_assets_to_file = save_assets_to_file
            self.graph = compile_workflow(langgraph_platform=False)
            self.base_config = {
                "configurable": {"thread_id": self.session_id},
                "metadata": {"source": "headless", "session_id": self.session_id},
            }
        except Exception as exc:  # pragma: no cover - initialization guard
            logger.error(f"Failed to initialize WorkflowRunner: {exc}")
            raise

    def run(
        self,
        user_query: str,
        conversation_history: list[dict[str, Any]] | None = None,
        retrieved_data: Any | None = None,
    ) -> RunResult:
        try:
            state = ChatbotState(
                session_id=self.session_id,
                user_query=user_query,
                generated_response="",
                conversation_history=conversation_history or [],
                retrieved_data=retrieved_data,
                parsed_query=ParsedQuery(parse_status="unparsed"),
            )
            return self._drive(state)
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.error(f"WorkflowRunner.run failed: {exc}")
            raise

    def resume_with_approval(self, decision: str) -> RunResult:
        try:
            if decision not in ("approved", "denied"):
                raise ValueError(f"Invalid approval decision: {decision}")
            self.graph.update_state(self.base_config, {"approval_result": decision})
            return self._drive(None)
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.error(f"WorkflowRunner.resume_with_approval failed: {exc}")
            raise

    def _coerce_state(self, values: Any) -> ChatbotState:
        try:
            if isinstance(values, ChatbotState):
                return values
            if isinstance(values, dict):
                return ChatbotState(**values)
            raise ValueError("Unsupported state payload")
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.error(f"Failed to coerce state: {exc}")
            raise

    def _handle_approval(self, state: ChatbotState) -> RunResult | None:
        try:
            if state.approval_required and not state.approval_result:
                if self.auto_approve:
                    self.graph.update_state(self.base_config, {"approval_result": "approved"})
                    return None
                return RunResult(state=state, pending=["approval"])
            return None
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.error(f"Approval handling failed: {exc}")
            raise

    def _handle_interrupts(self, pending: list[str]) -> bool:
        try:
            resume = False

            has_viz = any(node in pending for node in ["generate_visualization", "execute_visualization"])

            if self.auto_approve and has_viz:
                resume = True

            if "save_report" in pending and not has_viz and not self.save_assets_to_file:
                self.graph.update_state(self.base_config, {"skip_save": True})
                resume = True

            if self.auto_approve and "save_report" in pending:
                resume = True

            return resume
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.error(f"Interrupt handling failed: {exc}")
            raise

    def _drive(self, initial_state: ChatbotState | None) -> RunResult:
        try:
            next_input = initial_state
            pending: list[str] = []
            state_obj: ChatbotState | None = None

            while True:
                config = RunnableConfig(self.base_config)
                config["run_name"] = "Start Workflow" if next_input else "Resume Workflow"
                stream = self.graph.stream(next_input, config=config, stream_mode="updates")
                for _ in stream:
                    continue

                snapshot = self.graph.get_state(self.base_config)
                state_obj = self._coerce_state(snapshot.values)
                pending = list(snapshot.next or [])

                approval_result = self._handle_approval(state_obj)
                if approval_result is not None:
                    return approval_result

                if pending:
                    should_resume = self._handle_interrupts(pending)
                    next_input = None
                    if should_resume:
                        continue
                    return RunResult(state=state_obj, pending=pending)

                if state_obj is None:
                    raise ValueError("State unavailable after workflow run")

                return RunResult(state=state_obj, pending=[])
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.error(f"WorkflowRunner._drive failed: {exc}")
            raise
