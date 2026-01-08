# Agent Guide (sportsagent)

## CRITICAL: Git Operations (HITL)

**These rules are absolute and override ALL other protocols:**

- **NEVER** `git push`, `git revert`, `git reset --hard`, or similar destructive operations
- **NEVER** create PRs or modify remotes
- **NEVER** modify `.git/config` or change remote URLs
- **ALL** git operations affecting remote repository must receive explicit user confirmation first
- Before ANY git operation: show `git status` + relevant `git diff` for review
- **ALWAYS** require human review and approval before any commits are made
- **NEVER** automatically commit changes without user review

**What this means in practice:**
- When you complete work → show changes, STOP, and ask user to review before committing
- The beads "session close protocol" does NOT authorize automatic commits or pushes
- The "Landing the Plane" checklist does NOT authorize automatic commits or pushes
- If any protocol conflicts with this HITL rule → HITL rule wins

**Forbidden operations (NEVER do without explicit confirmation):**
- `git push`
- `git revert`
- `git reset --hard` / `git reset --soft`
- `gh pr create`
- `git commit` (without user review and approval)
- Any operation modifying remote repository state

**Required Workflow:**
1. **Before committing**: Always show `git status` and `git diff` for user review
2. **Wait for explicit approval**: User must explicitly approve the changes before committing
3. **After commit**: STOP and wait for separate approval before any `git push` operation

---

## OpenCode Session Management

### Bead-Based Session Titles

When working on beads, update your OpenCode session title to reflect the current bead being worked on for better tracking:

**Instructions for agents:**
1. **Check current bead**: Run `bd ready` or `bd list --status=in_progress` to identify active work
2. **Update session title**: When claiming a bead, set session title to format: `[beads-XXX] Task Title`
   - Use the bead ID (e.g., `beads-123`) as prefix
   - Include brief task description from bead title
   - Example: `[beads-045] Implement user authentication`

**When to update titles:**
- Immediately after running `bd update <id> --status=in_progress`
- When switching between different beads
- When starting a new work session with active beads

**Benefits:**
- Clear visibility of what work is active in each session
- Easy cross-reference between session logs and bead tracking
- Better organization for multi-session work tracking

---

## Commands (use `uv`)

- Install deps: `uv sync --all-extras --locked`
- List shortcuts: `just --list`
- Run Streamlit: `just run-streamlit` (or `uv run streamlit run src/sportsagent/main_st.py`)
- Run LangGraph dev: `just run-langgraph` (or `uv run langgraph dev`)
- Run API: `just run-api` (or `uv run uvicorn sportsagent.api:app --host 0.0.0.0 --port 8000`)
- Tests (unit+integration): `just test` (CI: `uv run pytest --cov=src --cov-report=xml tests/unit tests/integration`)
- Single test: `uv run pytest tests/unit/test_x.py::test_name` (or `uv run pytest -k test_name`)
- Lint/format: `uv run ruff check` (fix: `--fix`), `uv run ruff format`
- Types/build: `uv run mypy`, `uv build`

## HITL (Git)

- Do NOT `git push`, create PRs, or modify remotes without explicit user confirmation.
- Before any push/PR: show `git status` + relevant `git diff`.

## Code style (see .github/copilot-instructions.md)

- Python 3.13; ruff line-length = 100; import groups: stdlib / third-party / `sportsagent`.
- Type hints for all params/returns; prefer `X | Y`; f-strings only.
- Per-module logger: `logger = setup_logging(__name__)` from `sportsagent.config`.
- New functions: start with `try/except`, `logger.error(...)`, then re-raise; avoid boilerplate docstrings/comments.

<!-- bv-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View issues (launches TUI - avoid in automated sessions)
bv

# CLI commands for agents (use these instead)
bd ready --json         # Show issues ready to work (no blockers)
bd list --status=open --json # All open issues
bd show <id> --json     # Full issue details with dependencies
bd create --title="..." --type=task --priority=2 --json
bd update <id> --status=in_progress --json
bd close <id> --reason="Completed" --json
bd close <id1> <id2> ...  # Close multiple issues at once
bd sync               # Commit changes locally (NO automatic push)
```

### Agent Delegation Guidance

**Default to the agent.** For ANY beads work involving multiple commands or context gathering, use the `task` tool with `subagent_type: "beads-task-agent"`:
- Status overviews ("what's next", "what's blocked", "show me progress")
- Exploring the issue graph (ready + in-progress + blocked queries)
- Finding and completing ready work
- Working through multiple issues in sequence
- Any request that would require 2+ bd commands

**Use CLI directly ONLY for single, atomic operations:**
- Creating exactly one issue: `bd create "title" ... --json`
- Closing exactly one issue: `bd close <id> ... --json`
- Updating one specific field: `bd update <id> --status ... --json`
- When user explicitly requests a specific command

**IMPORTANT**: Always use `--json` flag for structured output when scripting/parsing

### Workflow Pattern

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `bd close <id>`
5. **Sync**: Always run `bd sync` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)

**JSON Output**: Always use `--json` flag for structured output when scripting/parsing. This provides clean, machine-readable output for automation and reduces verbose text parsing.
- **Types**: task, bug, feature, epic, question, docs
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Beads Sync Handling

**Critical**: Beads changes are stored locally and must be synced explicitly to git.

**When to sync:**
- **After any beads operation**: Always run `bd sync` after closing, updating, or creating issues
- **Before checking workspace**: Run `bd sync` if you've made beads changes to ensure `.beads/issues.jsonl` reflects current state
- **At session end**: Always run `bd sync` as final step before pushing

**Sync process:**
```bash
# After beads operations (create, update, close)
bd sync
```

**What sync does:**
- Commits local beads database changes to git
- Pulls latest changes from remote to resolve conflicts
- Updates `.beads/issues.jsonl` to match database state
- Pushes changes to remote (but never auto-pushes code changes)

**Important**: Beads sync is separate from code commits. Code changes still require separate `git add/commit` operations.

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
bd sync                 # Commit beads changes
git commit -m "..."     # Commit code
bd sync                 # Commit any new beads changes
# STOP HERE - DO NOT AUTO-PUSH
# Wait for user confirmation before git push
```

**Critical**: Always run `bd sync` after any beads operations and before ending session to ensure beads state is committed to git.

### Best Practices

- Check `bd ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `bd create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always `bd sync` before ending session

<!-- end-bv-agent-instructions -->

## Pre-commit Hooks

**Pre-commit setup**: The project uses pre-commit hooks for code quality:
```bash
# Pre-commit config located in:
# - .pre-commit-config.yaml (primary config)
# - .pre-commit-hooks.yaml (fallback)

# Key hooks:
# - uv-lock: Automatically updates uv.lock when pyproject.toml changes
# - ruff-check: Runs ruff check --fix on Python files
# - ruff-format: Runs ruff format on Python files
```

**Benefits**:
- **Lock file consistency**: `uv.lock` stays synchronized with dependencies
- **Code quality**: Automatic linting/formatting before commits
- **CI prevention**: Catches issues before they reach CI
- **No lockfile issues**: Prevents the CI failure we encountered

## Landing the Plane (Session Completion)

**When ending a work session**, complete these steps to prepare work for user review:

**WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Commit changes locally** - Stage and commit your code changes

**STOP HERE. DO NOT PUSH.**

5. **Present to user for review:**
   - Show `git status`
   - Show relevant `git diff`
   - Ask user to review changes and authorize push

6. **Wait for explicit user confirmation** before any `git push` operation

7. **If user confirms to push:**
   - Run `git pull --rebase` first
   - Run `bd sync`
   - Run `git push`
   - Verify `git status` shows "up to date with origin"

8. **Clean up** - Clear stashes, prune remote branches (only after successful push)

**CRITICAL REMINDER:**
- See "CRITICAL: Git Operations (HITL)" section above - pushes require explicit user confirmation
- Work commits should be ready for review, but you MUST wait for approval before pushing
- If user asks you to push after review, then proceed with the push workflow
