<!-- SPDX-License-Identifier: MIT -->

# AgentWS

A git-friendly, human-readable workspace for coordinating AI agents. AgentWS
uses Markdown files, shell scripts, and directories so task state, role
instructions, and job handoffs stay inspectable with ordinary tools.

AgentWS gives a project durable task state, project-specific agent roles, and a
job queue that coding agents can inspect and operate locally.

## TL;DR for Humans

From your project, ask your coding agent to install AgentWS from GitHub:

```text
Install AgentWS here from https://github.com/glguida/agentws.
```

Run AgentWS:

```sh
agentws/tools/agentws
```

This starts the built-in `console` assistant, the configured team, and the
local web interface. By default it listens on the first free port at or above
`127.0.0.1:4137` and prints the local URL to open. Use `--verbose` when you
want to see agent output in the terminal:

```sh
agentws/tools/agentws --verbose
```

Without `--verbose`, agents still run and transcripts are written under
`agentws/agents/`.

Then work out a task with your coding agent and tell it to dispatch the task to
AgentWS:

```text
Dispatch this task to AgentWS.
```

The coding agent should read the rest of this README and use the AgentWS tools.

Watch progress in the local web interface, or with the lower-level files and
commands:

```sh
agentws/tools/agentws
agentws/bin/job-list
tail -f agentws/tasks/<task-id>/log.md
tail -f agentws/agents/<agent-name>/transcript.log
```

## TL;DR for Agents

If you are an AI agent asked to install AgentWS in a repository, clone AgentWS
from GitHub and install the local template exactly as shown below.

Install from the target project root:

```sh
tmp="$(mktemp -d)"
git clone https://github.com/glguida/agentws.git "$tmp/agentws"
cp -r "$tmp/agentws/template" ./agentws
agentws/bin/job-init
printf '%s\n' "agentws/tasks/" "agentws/jobs/" "agentws/agents/" >> .gitignore
```

The runtime directories must be added to `.gitignore`:

```text
agentws/tasks/
agentws/jobs/
agentws/agents/
```

Keep these project configuration files:

```text
agentws/AGENTS.md
agentws/default.team
agentws/roles/
agentws/bin/
agentws/tools/
```

Do not commit runtime state; it must be ignored in `.gitignore`:

```text
agentws/tasks/
agentws/jobs/
agentws/agents/
```

When done, tell the human:

```sh
agentws/tools/agentws
```

They can add `--verbose` if they want agent output printed in the terminal.

Tasks are dispatched with the installed `task-create` tool:

```sh
agentws/bin/task-create <task-id> <spec-file>
```

If asked to dispatch work to AgentWS, create a complete task spec file and run
`task-create`.

## Full Install Reference

AgentWS has one install template:

```text
template    local task folders, local job queue, standard roles, committer workflow
```

Role definitions are included in the template:

```text
template/roles/planner.md
template/roles/implementer.md
template/roles/reviewer.md
template/roles/committer.md
template/roles/console.md
```

Install:

```sh
tmp="$(mktemp -d)"
git clone https://github.com/glguida/agentws.git "$tmp/agentws"
cp -r "$tmp/agentws/template" ./agentws
agentws/bin/job-init
printf '%s\n' "agentws/tasks/" "agentws/jobs/" "agentws/agents/" >> .gitignore
```

Requirements are summarized near the bottom of this README. There is no Python
package install or build step.

Commit or otherwise keep the reusable project configuration:

```text
.gitignore
agentws/AGENTS.md
agentws/default.team
agentws/roles/
agentws/bin/
agentws/tools/
```

Do not commit runtime state. These paths must be in `.gitignore`:

```text
agentws/tasks/
agentws/jobs/
agentws/agents/
```

After install, create work with:

```sh
agentws/bin/task-create <task-id> <spec-file>
```

Run AgentWS:

```sh
agentws/tools/agentws
```

This starts the built-in `console` assistant, the configured team, and the
local web interface. By default it listens on the first free port at or above
`127.0.0.1:4137` and prints the local URL to open. For live terminal agent
output, add `--verbose`:

```sh
agentws/tools/agentws --verbose
```

For a read-only web interface without starting agents, use:

```sh
agentws/tools/agentws --no-team
```

## How It Works

The model is:

```text
task -> jobs -> named agent runs
```

```text
agentws/
  AGENTS.md
  default.team
  roles/
  bin/
  tools/
  tasks/
  jobs/
  agents/
```

Only `AGENTS.md`, `default.team`, `roles/`, `bin/`, and `tools/` are
project configuration. `tasks/`, `jobs/`, and `agents/` are runtime state and
must be ignored.

A task is the long-lived objective:

```text
tasks/<task-id>/
  spec.md
  state
  log.md
  result.md
```

A job is one role-scoped unit of work inside a task:

```text
jobs/<job-id>/
  task-id
  role
  spec.md
  status
  agent-id
  log.md
  workspace/
  lock/
```

A named agent has a durable transcript:

```text
agents/<agent-name>/
  name
  role
  current-job
  engine
  prompt.md
  transcript.log
  error.log
```

The top-level local interface is `agentws/tools/agentws`. It starts the
built-in `console` assistant, starts the configured team, serves the installed
AgentWS root by default, and reads task, job, and agent state from the local
runtime directories. `run_agentws` remains available as the lower-level team
runner.

Agent output is appended to `agents/<agent-name>/transcript.log`. The Python
runner renders structured JSON events into a readable transcript instead of
saving raw JSON. Job logs point to the agent transcript and remain short
summaries. CLI diagnostics are saved under the agent directory as `error.log`.
With `run_agentws --verbose`, rendered agent output is also printed to the
terminal with each line prefixed by the agent name; live errors are prefixed and
printed on stderr.

`task-create` creates the task and the first planner job. Task commands are the
public interface:

```sh
agentws/bin/task-create <task-id> <spec-file>
agentws/bin/task-show <task-id>
agentws/bin/task-comment <task-id> <message>
agentws/bin/task-state <task-id> open
agentws/bin/task-state <task-id> done -m "completed"
agentws/bin/task-result <task-id> <result-file>
agentws/bin/task-list
```

Task states are deliberately small:

```text
open
done
```

Jobs have internal execution status so AgentWS can recover from dead agent
processes. Task state is only the visible task lifecycle. Planner owns task
completion and records the final result with `task-result`, which also marks
the task `done`.

For repository-changing tasks, planner creates or names a dedicated work branch
and worktree for the change and records the original base checkout, exact base
branch, base commit, worktree, and work branch. Implementer and reviewer work
only in that worktree. The committer is the local integration role: after review
approval, it checks out the named base branch in the original base checkout,
merges the approved work branch there, and verifies again in that base checkout.

Every non-planner job reports its outcome back to planner as a planner job. Any
agent that learns durable undocumented project knowledge creates a planner job
asking planner to route a documentation update through implementer, reviewer,
and committer.

## Team File

`default.team` is line-oriented:

```text
# <name> <role> <agent> [model]
planner-1 planner pi
implementer-1 implementer pi
reviewer-1 reviewer pi
committer-1 committer pi
```

The agent field is one of `pi`, `pi-interactive`, `codex`, or `claude`.
`pi-interactive` keeps the normal role/job protocol but also exposes a live
transcript and message box in the local web interface.

The built-in `console` assistant is started by `agentws/tools/agentws` itself.
It is not a team-file entry and does not have a queued job. It uses the
`console` role to help the human draft task specs, dispatch tasks, and inspect
or manage the local AgentWS system. The web interface exposes it in the `Chat`
tab for normal use. Agent inspectors still provide the lower-level transcript
view with explicit `Send` and `Steer` controls.

## Roles

Role source files are installed with the template:

```text
agentws/roles/
```

- `planner`: coordinates the task, updates it with `task-comment`, creates
  follow-up jobs, and records the final result with `task-result`.
- `implementer`: does concrete work and creates reviewer jobs.
- `reviewer`: reviews artifacts and routes pass/fix/blocker outcomes.
- `committer`: integrates approved work locally.
- `console`: interactive assistant for task intake and AgentWS management.

Documentation updates are routed by planner through implementer, reviewer, and
committer.

## Requirements

- `sh`
- Python 3
- `pi` on `PATH` for the default team and built-in console
- optional: `codex` or `claude` on `PATH` only if the team file is changed to
  use those agent types
- a browser for the local `agentws/tools/agentws` web interface

`agentws/tools/agentws` and `agentws/tools/agent` use Python 3 stdlib only.
Python tools are executable scripts with `#!/usr/bin/env python3`; do not run or
install them through compilation steps.

## Commands

```sh
agentws/bin/job-init
agentws/bin/task-create <task-id> <spec-file>
agentws/bin/task-show <task-id>
agentws/bin/task-comment <task-id> <message>
agentws/bin/task-state <task-id> open|done [-m message]
agentws/bin/task-result <task-id> <result-file>
agentws/bin/task-list
agentws/bin/job-create <job-id> -r <role> -t <task-id> <spec-file>
agentws/bin/job-list [status]
agentws/tools/agentws [--no-team] [--no-console] [--verbose] [--root path] [--host host] [--port port] [team-file]
agentws/tools/run_agentws [--verbose] [team-file]
agentws/tools/agent [--pi|--codex|--claude] [--headless] [-m model] <role> <agent-name>
agentws/tools/agent-pi-interactive [--console] [--headless] [-m model] [role] [agent-name]
```

Lower-level job helper behavior is described in `agentws/AGENTS.md`.

## License

MIT. See [LICENSE](LICENSE).
