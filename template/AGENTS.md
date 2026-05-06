# AgentWS - Filesystem Job Protocol

You are a job-scoped agent. A shell supervisor claimed one job and started this
fresh process to handle that job only.

Do not wait for more jobs. Do not claim another job. Process the assigned job,
create any required follow-up jobs, mark the assigned job done, failed, or
released, and exit.

## Assigned Job

The assigned job is normally provided in the launch prompt and in environment:

```text
AGENTWS_JOB_ID=<job-id>
AGENTWS_JOB_ROLE=<role>
AGENTWS_RUN_ID=<opaque run token>
```

Read these files before acting:

```text
jobs/<job-id>/spec.md
jobs/<job-id>/log.md
roles/<role>.md
```

The role file defines role-specific behavior. The job spec defines the actual
work and follow-up handoff.

## Job Layout

Each job is a directory under `jobs/`:

```text
jobs/<job-id>/
  spec.md          complete job instructions
  role             role assigned to this job
  status           pending, claimed, running, done, or failed
  run.id           opaque token for the active run
  agent.id         human-readable active runner metadata
  log.md           append-only work log
  transcript.log   process output captured by the supervisor
  workspace/       scratch area for this job
```

Use helper scripts in `bin/` for queue state. Do not edit `status`, `run.id`,
or lock files directly.

## Statuses

Valid statuses are:

- `pending`: available to be claimed by the supervisor
- `claimed`: reserved by the supervisor
- `running`: actively being processed
- `done`: finished successfully
- `failed`: cannot be completed by this workflow

The normal lifecycle is:

```text
pending -> claimed -> running -> done
                         |
                         v
                       failed
```

`job-release` moves `claimed` or `running` back to `pending` for temporary
blockers.

## Run Token

`run.id` is an opaque coordination token. Transition helpers compare
`AGENTWS_RUN_ID` with `jobs/<job-id>/run.id`. This lets the job-scoped agent
process complete a job that the shell supervisor claimed for it.

It is not a security boundary. It is only a filesystem coordination capability.

## Logging

Append useful work notes to `jobs/<job-id>/log.md` as you go. Use this shape:

```markdown
## <ISO-8601 timestamp> - <short summary>

<what was done, decisions made, files changed, commands run, and results>
```

The transition helpers also append short entries for start, done, fail, release,
and reaping events.

## Creating Follow-Up Jobs

Create jobs atomically with a complete spec file. Write the spec somewhere
temporary first, then pass it to `job-create`:

```sh
cat > /tmp/<new-job-id>-spec.md <<'EOF'
# <title>

## Objective
<complete objective>

## Context
<background, dependencies, artifacts, and prior jobs>

## Acceptance Criteria
<checks or evidence that prove completion>

## When Done
<exact follow-up job or completion action>
EOF

bin/job-create <new-job-id> -r <role> /tmp/<new-job-id>-spec.md
```

Do not create empty jobs. Do not create a job and then edit its `spec.md`; that
allows another process to claim incomplete work.

## Completing This Job

When the job is complete, run exactly one terminal transition:

```sh
bin/job-done <job-id> -m "<summary>"
bin/job-fail <job-id> -m "<reason>"
bin/job-release <job-id> -m "<temporary blocker>"
```

Use `job-done` only after required follow-up jobs already exist.

## Problem Handling

- If work succeeds, create required follow-up jobs and mark this job done.
- If the spec is invalid, impossible, or contradictory, mark this job failed.
- If the blocker is temporary and the same job may be valid later, release it.
- If another role needs to decide what happens next, create a planner job first.

## Target Modification Isolation

If a job modifies a Git-backed target, use a dedicated branch and worktree unless
the job spec gives a stricter local workflow. Record the branch, worktree, and
base commit in the job log before editing. Follow-up review or commit jobs must
name the artifact they should inspect or integrate.

## Helpers

- `bin/job-create <job-id> -r <role> <spec-file>`
- `bin/job-claim [job-id] [-r <role>]`
- `bin/job-start <job-id>`
- `bin/job-done <job-id> -m <message>`
- `bin/job-release <job-id> -m <message>`
- `bin/job-fail <job-id> -m <message>`
- `bin/job-list [status]`
- `bin/job-mine`
- `bin/job-wait [-r <role>]`
- `bin/job-watch <status>`
- `bin/job-orphans`
- `bin/job-reset-orphans`
- `bin/job-reap [minutes]`
