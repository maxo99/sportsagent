import argparse
import logging
from collections.abc import Callable

import pytest

from sportsagent import cli
from sportsagent.runner import RunResult

logger = logging.getLogger(__name__)


def test_build_parser_chat_command() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["chat", "hello", "--session-id", "abc", "--save-assets-to-file"])

    assert args.command == "chat"
    assert args.prompt == "hello"
    assert args.session_id == "abc"
    assert args.save_assets_to_file is True


def test_run_chat_invokes_runner(
    monkeypatch: pytest.MonkeyPatch,
    fake_runner_factory: Callable[[list[RunResult]], type],
    make_run_result: Callable[..., RunResult],
) -> None:
    responses = [make_run_result()]
    FakeRunner = fake_runner_factory(responses)
    monkeypatch.setattr(cli, "WorkflowRunner", FakeRunner)
    monkeypatch.setattr(cli, "_display_result", lambda result: None)
    monkeypatch.setattr(cli, "_prompt_for_input", lambda message: "")

    args = argparse.Namespace(
        command="chat",
        prompt="first",
        session_id=None,
        auto_approve=False,
        save_assets_to_file=False,
    )

    cli._run_chat(args)

    runner = FakeRunner.instances[-1]
    assert runner.run_calls[0][0] == "first"
    assert runner.resume_calls == []


def test_run_chat_handles_approval(
    monkeypatch: pytest.MonkeyPatch,
    fake_runner_factory: Callable[[list[RunResult]], type],
    make_run_result: Callable[..., RunResult],
) -> None:
    approval_result = make_run_result(pending=["approval"])
    final_result = make_run_result()
    responses = [approval_result, final_result]
    FakeRunner = fake_runner_factory(responses)
    inputs = iter(["y", ""])

    monkeypatch.setattr(cli, "WorkflowRunner", FakeRunner)
    monkeypatch.setattr(cli, "_display_result", lambda result: None)
    monkeypatch.setattr(cli, "_prompt_for_input", lambda message: next(inputs))

    args = argparse.Namespace(
        command="chat",
        prompt="question",
        session_id=None,
        auto_approve=False,
        save_assets_to_file=False,
    )

    cli._run_chat(args)

    runner = FakeRunner.instances[-1]
    assert runner.resume_calls == ["approved"]
    assert runner.run_calls[0][0] == "question"
