import argparse
from typing import Any

from sportsagent.config import settings, setup_logging
from sportsagent.runner import RunResult, WorkflowRunner

logger = setup_logging(__name__)


def _build_parser() -> argparse.ArgumentParser:
    try:
        parser = argparse.ArgumentParser(prog="sportsagent", description="SportsAgent CLI")
        subparsers = parser.add_subparsers(dest="command", required=True)

        chat_parser = subparsers.add_parser("chat", help="Start chat session")
        chat_parser.add_argument("prompt", nargs="?", help="Initial prompt to send")
        chat_parser.add_argument("--session-id", dest="session_id", help="Session identifier")
        chat_parser.add_argument(
            "--auto-approve",
            action="store_true",
            default=settings.AUTO_APPROVE_DEFAULT,
            help="Automatically approve HITL steps",
        )
        chat_parser.add_argument(
            "--save-assets-to-file",
            action="store_true",
            default=settings.SAVE_ASSETS_DEFAULT,
            help="Persist visualization/report assets to disk",
        )
        return parser
    except Exception as exc:  # pragma: no cover - parser guard
        logger.error(f"Failed to build parser: {exc}")
        raise


def _prompt_for_input(message: str) -> str:
    try:
        return input(message).strip()
    except Exception as exc:  # pragma: no cover - IO guard
        logger.error(f"Input prompt failed: {exc}")
        raise


def _prompt_for_approval(auto_approve: bool) -> str:
    try:
        if auto_approve:
            return "approved"
        decision = _prompt_for_input("Approve data retrieval? [y/N]: ")
        return "approved" if decision.lower() in {"y", "yes"} else "denied"
    except Exception as exc:  # pragma: no cover - IO guard
        logger.error(f"Approval prompt failed: {exc}")
        raise


def _display_result(result: RunResult) -> None:
    try:
        print(f"Assistant: {result.state.generated_response}")
        if result.state.visualization and result.state.skip_save:
            print("Visualization available (skipped saving).")
        if result.state.visualization and not result.state.skip_save:
            print(f"Visualization stored in {settings.ASSET_OUTPUT_DIR}")
    except Exception as exc:  # pragma: no cover - display guard
        logger.error(f"Display failed: {exc}")
        raise


def _run_chat(args: argparse.Namespace) -> None:
    try:
        runner = WorkflowRunner(
            session_id=args.session_id,
            auto_approve=args.auto_approve,
            save_assets_to_file=args.save_assets_to_file,
        )
        conversation_history: list[dict[str, Any]] = []
        retrieved_data: Any | None = None

        prompt = args.prompt or _prompt_for_input("You: ")
        while prompt:
            result = runner.run(prompt, conversation_history=conversation_history, retrieved_data=retrieved_data)
            _display_result(result)

            while result.pending == ["approval"]:
                decision = _prompt_for_approval(args.auto_approve)
                result = runner.resume_with_approval(decision)
                _display_result(result)

            conversation_history = result.state.conversation_history
            retrieved_data = result.state.retrieved_data
            prompt = _prompt_for_input("You: ")
    except KeyboardInterrupt:  # pragma: no cover - user abort
        print("\nSession ended.")
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.error(f"CLI chat failed: {exc}")
        raise


def main() -> None:
    try:
        parser = _build_parser()
        args = parser.parse_args()
        if args.command == "chat":
            _run_chat(args)
        else:
            parser.print_help()
    except Exception as exc:  # pragma: no cover - entry guard
        logger.error(f"CLI failed: {exc}")
        raise


if __name__ == "__main__":
    main()
