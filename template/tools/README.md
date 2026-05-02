# AgentWS Tools

This directory contains project-local helper tools for AgentWS.

## `run_agentws.sh`

`run_agentws.sh` starts a tmux session for the current Git repository and
launches one `pi` agent per row in `agentws/default.team`.

From the repository root:

```sh
agentws/tools/run_agentws.sh
agentws/tools/run_agentws.sh -m sonnet
agentws/tools/run_agentws.sh -n
```

Options:

- `-m <model>`: pass `--model <model>` to every `pi` agent.
- `-n`: create the tmux session without attaching.
- `-c <path>`: use a different team file path.

The default team file is resolved from the current Git repository root:

```text
<git-root>/agentws/default.team
```

Team file rows are:

```text
<tmux-window-name> <agent-role>
```

Blank lines and `#` comments are ignored, including inline comments.
Each launched agent receives only:

```text
You are a <agent-role>
```
