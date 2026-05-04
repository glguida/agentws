# AgentWS Tools

This directory contains project-local helper tools for AgentWS.

## `run_agentws.sh`

`run_agentws.sh` starts a tmux session for the current Git repository and
launches one `pi` agent per row in `agentws/default.team`.

From the repository root:

```sh
agentws/tools/run_agentws.sh <project-name>
agentws/tools/run_agentws.sh -m sonnet <project-name>
agentws/tools/run_agentws.sh -n <project-name>
```

Options:

- `-m <model>`: pass `--model <model>` to every `pi` agent.
- `-n`: create the tmux session without attaching.
- `-c <path>`: use a different team file path.

The final positional argument is the tmux session name. For human-run project
sessions, pass the project name explicitly. If omitted, the session name defaults
to `agentws-session`.

The default team file is resolved from the current Git repository root:

```text
<git-root>/agentws/default.team
```

Team file rows are:

```text
<tmux-window-name> <agent-role>
```

Blank lines and `#` comments are ignored, including inline comments.
Each `<agent-role>` must have a matching `agentws/roles/<agent-role>.md` file.
Each launched agent receives only:

```text
You are a <agent-role>
```
