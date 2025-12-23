import asyncio
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sportsagent.config import settings, setup_logging
from sportsagent.runner import RunResult, WorkflowRunner

logger = setup_logging(__name__)
app = FastAPI()

_session_store: dict[str, WorkflowRunner] = {}


class ChatTurnRequest(BaseModel):
    user_query: str
    session_id: str | None = None
    auto_approve: bool | None = None
    save_assets_to_file: bool | None = None


class ApprovalRequest(BaseModel):
    session_id: str
    decision: str


class ChatResponse(BaseModel):
    session_id: str
    generated_response: str
    pending: list[str]
    approval_required: bool
    needs_visualization: bool
    asset_dir: str


def _get_runner(
    session_id: str | None,
    auto_approve: bool | None,
    save_assets_to_file: bool | None,
) -> WorkflowRunner:
    try:
        target_session = session_id or str(uuid.uuid4())
        runner = _session_store.get(target_session)
        if runner is None:
            runner = WorkflowRunner(
                session_id=target_session,
                auto_approve=auto_approve
                if auto_approve is not None
                else settings.AUTO_APPROVE_DEFAULT,
                save_assets_to_file=(
                    save_assets_to_file
                    if save_assets_to_file is not None
                    else settings.SAVE_ASSETS_DEFAULT
                ),
            )
            _session_store[target_session] = runner
        else:
            if auto_approve is not None:
                runner.auto_approve = auto_approve
            if save_assets_to_file is not None:
                runner.save_assets_to_file = save_assets_to_file
        return runner
    except Exception as exc:
        logger.error(f"Failed to fetch runner: {exc}")
        raise


def _format_response(result: RunResult) -> ChatResponse:
    try:
        return ChatResponse(
            session_id=result.state.session_id,
            generated_response=str(result.state.generated_response),
            pending=result.pending,
            approval_required=result.state.approval_required,
            needs_visualization=result.state.needs_visualization,
            asset_dir=str(settings.ASSET_OUTPUT_DIR),
        )
    except Exception as exc:
        logger.error(f"Failed to format response: {exc}")
        raise


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    try:
        return {"status": "ok"}
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        raise


@app.post("/chat/turn", response_model=ChatResponse)
async def chat_turn(payload: ChatTurnRequest) -> ChatResponse:
    try:
        runner = _get_runner(payload.session_id, payload.auto_approve, payload.save_assets_to_file)
        result = await asyncio.to_thread(runner.run, payload.user_query)
        return _format_response(result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Chat turn failed: {exc}")
        raise HTTPException(status_code=500, detail="chat failed") from exc


@app.post("/chat/approve", response_model=ChatResponse)
async def approve(payload: ApprovalRequest) -> ChatResponse:
    try:
        runner = _session_store.get(payload.session_id)
        if runner is None:
            raise HTTPException(status_code=404, detail="unknown session")
        decision = payload.decision.lower()
        if decision not in {"approved", "denied"}:
            raise HTTPException(status_code=400, detail="decision must be approved or denied")
        result = await asyncio.to_thread(runner.resume_with_approval, decision)
        return _format_response(result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Approval failed: {exc}")
        raise HTTPException(status_code=500, detail="approval failed") from exc
