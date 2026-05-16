# AgentWS Tools

This directory contains local helper tools for an installed AgentWS directory.

The shell launchers require `sh` and whichever agent CLI is selected (`pi`,
`codex`, or `claude`). `tools/agent` uses Python 3 stdlib only.

## `run_agentws`

`run_agentws` starts a named team from a team file and restarts each agent as
it exits. By default it runs agents headless. Use `--verbose` to print each
agent's rendered transcript output to the terminal, prefixed by agent name.

```sh
agentws/tools/run_agentws --verbose
agentws/tools/run_agentws
```

Team file format:

```text
# <name> <role> <agent> [model]
planner-1 planner pi
implementer-1 implementer codex
reviewer-1 reviewer claude sonnet
```

## `agent`

`agent` starts one named agent, claims one pending job for that agent's role,
records the job in `agents/<agent-name>/current-job`, and renders CLI event
output to `agents/<agent-name>/transcript.log`.
By default it also prints the rendered transcript to stdout. Use `--headless`
to write files only.

From the target project root:

```sh
# Start a Pi planner agent.
agentws/tools/agent --pi planner planner-1

# Start a named Codex implementer agent.
agentws/tools/agent --codex implementer implementer-1

# Start a Claude reviewer agent with a specific model.
agentws/tools/agent --claude -m sonnet reviewer reviewer-1
```

Options:

- `--pi`: use Pi. This is the default.
- `--codex`: use Codex CLI.
- `--claude`: use Claude Code.
- `--headless`: do not print the rendered transcript to stdout.
- `-m <model>`: pass a model name to the selected CLI.

CLI stderr is saved in `error.log`.

The agent name is mandatory. `agent` calls `bin/agent-new`, `bin/job-wait`, and
`bin/job-claim`; the agent itself starts and completes the job according to
`AGENTS.md`. The rendered transcript is stored only in
`agents/<agent-name>/transcript.log`; the job log points to that file.

## Task Commands

Task commands operate on local folders under `agentws/tasks/`:

```sh
agentws/bin/task-create <task-id> <spec-file>
agentws/bin/task-show <task-id>
agentws/bin/task-comment <task-id> <message>
agentws/bin/task-state <task-id> open
agentws/bin/task-state <task-id> done -m "completed"
agentws/bin/task-result <task-id> <result-file>
agentws/bin/task-list
```

## `bin/agent-new`

`bin/agent-new <agent-id> <role>` creates a named agent directory when needed
and prints its path. If the agent already has a claimed or running job, it exits
with an error instead.
