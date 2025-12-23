import logging
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from sportsagent import api
from sportsagent.runner import RunResult

logger = logging.getLogger(__name__)


@pytest.fixture
def client() -> TestClient:
    api._session_store.clear()
    return TestClient(api.app)


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_turn_invokes_runner(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    fake_runner_factory: Callable[[list[RunResult]], type],
    make_run_result: Callable[..., RunResult],
) -> None:
    run_result = make_run_result()
    FakeRunner = fake_runner_factory([run_result])
    FakeRunner.instances.clear()

    monkeypatch.setattr(api, "WorkflowRunner", FakeRunner)
    monkeypatch.setattr(api, "_session_store", {})

    response = client.post("/chat/turn", json={"user_query": "hello"})

    assert response.status_code == 200
    body = response.json()
    assert body["generated_response"] == run_result.state.generated_response
    assert body["pending"] == []

    runner = FakeRunner.instances[-1]
    assert runner.run_calls[0][0] == "hello"


def test_approve_resumes_runner(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    fake_runner_factory: Callable[[list[RunResult]], type],
    make_run_result: Callable[..., RunResult],
) -> None:
    final_result = make_run_result()
    FakeRunner = fake_runner_factory([final_result])
    FakeRunner.instances.clear()
    runner = FakeRunner()

    monkeypatch.setattr(api, "_session_store", {"session": runner})

    response = client.post("/chat/approve", json={"session_id": "session", "decision": "approved"})

    assert response.status_code == 200
    assert response.json()["pending"] == []
    assert runner.resume_calls == ["approved"]
