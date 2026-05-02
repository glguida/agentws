# Practical Use

The usual flow is:

1. Start the worker team.
2. Use one coding agent to choose the work and create a plan job.
3. Ask that same coding agent for status while the team works.

## 1. Start The Team

From the project root:

```sh
agentws/tools/run_agentws.sh
```

This starts the agents listed in `agentws/default.team`.

## 2. Use One Coding Agent

In another terminal:

```sh
cd agentws
pi
```

Use your favorite coding agent here: pi.dev, Claude, Codex, or another coding
agent.

Ask it to help decide what feature to implement. Once the feature is clear, ask:

```text
Write a detailed AgentWS spec for this task and create it as a plan job.
```

The running team will pick up the plan job, split it into implementation work,
and start processing the resulting jobs.

## 3. Ask For Status

At any time, ask the same coding agent:

```text
What is the status?
```

It can inspect the job queue and summarize what the team is working on.
