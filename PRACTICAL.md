# Practical Use

From your project, ask your coding agent to install AgentWS:

```text
Install AgentWS here from https://github.com/glguida/agentws.
```

Start the team with live terminal output:

```sh
agentws/tools/run_agentws --verbose
```

Run `agentws/tools/run_agentws` without `--verbose` for quieter background use.

The installer should clone `https://github.com/glguida/agentws`, copy its
`template/` directory into `agentws/`, run `agentws/bin/job-init`, and add
`agentws/tasks/`, `agentws/jobs/`, and `agentws/agents/` to `.gitignore`.

Then work out the task with your coding agent and tell it to dispatch it to
AgentWS:

```text
Dispatch this task to AgentWS.
```

Watch progress:

```sh
agentws/bin/job-list
tail -f agentws/tasks/<task-id>/log.md
tail -f agentws/agents/<agent-name>/transcript.log
```
