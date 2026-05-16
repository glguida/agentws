<!-- SPDX-License-Identifier: MIT -->

# Practical Use

From your project, ask your coding agent to install AgentWS:

```text
Install AgentWS here from https://github.com/glguida/agentws.
```

Run AgentWS:

```sh
agentws/tools/agentws
```

This starts the built-in `console` assistant, the configured team, and the
local web interface. By default it listens on the first free port at or above
`127.0.0.1:4137` and prints the local URL to open. Use `--verbose` for live
terminal output:

```sh
agentws/tools/agentws --verbose
```

Without `--verbose`, transcripts are still written under `agentws/agents/`.

The installer should clone `https://github.com/glguida/agentws` into a fresh
temporary directory, copy its `template/` directory into `agentws/`, run
`agentws/bin/job-init`, and add
`agentws/tasks/`, `agentws/jobs/`, and `agentws/agents/` to `.gitignore`.

Then work out the task with your coding agent and tell it to dispatch it to
AgentWS:

```text
Dispatch this task to AgentWS.
```

Watch progress in the web interface, or with the lower-level files and commands:

```sh
agentws/tools/agentws
agentws/bin/job-list
tail -f agentws/tasks/<task-id>/log.md
tail -f agentws/agents/<agent-name>/transcript.log
```
