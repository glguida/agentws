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

Start the AgentWS team. Use `--verbose` when you want to see agent output in
the terminal:

```sh
agentws/tools/run_agentws --verbose
```

Use `agentws/tools/run_agentws` without `--verbose` for quieter background
runs; transcripts are still written under `agentws/agents/`.

Then work out a task with your coding agent and tell it to dispatch the task to
AgentWS:

```text
Dispatch this task to AgentWS.
```

The coding agent should read the rest of this README and use the AgentWS tools.

Watch progress:

```sh
agentws/bin/job-list
tail -f agentws/tasks/<task-id>/log.md
tail -f agentws/agents/<agent-name>/transcript.log
```

## TL;DR for Agents

If you are an AI agent asked to install AgentWS in a repository, clone AgentWS
from GitHub and install the local template exactly as shown below.

Install from the target project root:

```sh
git clone https://github.com/glguida/agentws.git /tmp/agentws
cp -r /tmp/agentws/template ./agentws
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
agentws/tools/run_agentws --verbose
```

They can run `agentws/tools/run_agentws` without `--verbose` if they do not want
agent output printed in the terminal.

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
```

Install:

```sh
git clone https://github.com/glguida/agentws.git /tmp/agentws
cp -r /tmp/agentws/template ./agentws
agentws/bin/job-init
printf '%s\n' "agentws/tasks/" "agentws/jobs/" "agentws/agents/" >> .gitignore
```

AgentWS expects `sh`, Python 3, and whichever agent CLI the team file uses
(`pi`, `codex`, or `claude`) to be available on `PATH`. `agentws/tools/agent`
uses Python 3 stdlib only. Python tools are executable scripts with
`#!/usr/bin/env python3`; do not run or install them through compilation steps.

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

Then start the configured team:

```sh
agentws/tools/run_agentws --verbose
```

For a quiet run, omit `--verbose`:

```sh
agentws/tools/run_agentws
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

The agent field is one of `pi`, `codex`, or `claude`.

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

Documentation updates are routed by planner through implementer, reviewer, and
committer.

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
agentws/tools/run_agentws [--verbose] [team-file]
agentws/tools/agent [--pi|--codex|--claude] [--headless] [-m model] <role> <agent-name>
```

Lower-level job helper behavior is described in `agentws/AGENTS.md`.

## License

Public domain. Use it however you want.
