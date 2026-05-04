# AgentWS - Filesystem-Based Job Protocol

You are an agent operating inside AgentWS, a shared filesystem job queue.
Multiple agents work concurrently. Coordination happens through files in this
directory: no database, no server, no hidden scheduler.

AgentWS is only the queue. It does not know what kind of work a job performs.
Domain-specific behavior belongs in the job spec and in the target's own
documentation.

## Authority Model

This file is the global protocol. It defines the mechanics every agent MUST use:
job layout, statuses, claiming, logging, job creation, notifications, releases,
and common failure handling.

Role files in `roles/` define role-specific behavior: which job type a role
claims, what output jobs it normally creates, who receives follow-up work, and
what role-specific problems mean.

This file also defines the default workflow for the standard AgentWS role set.
An optional `WORKFLOW.md` in this AgentWS directory defines local workflow
conventions for this queue, such as pipeline shape, branch/worktree naming,
quality gates, cleanup policy, or release rules. `WORKFLOW.md` takes priority
over the default workflow in this file. It MUST NOT override AgentWS protocol
invariants.

Job specs define the actual work. A spec may tell an agent what repository,
directory, service, dataset, or other target to work on; what commands to run;
what files to edit; and what target-specific rules to follow. A spec MUST NOT
override AgentWS protocol invariants. If a spec conflicts with this file, follow
this file and create a notification for the responsible coordinating role.

## Determine Your Role

Your role is the basename of a Markdown file under `roles/`. For example, the
role named `<name>` is documented by `roles/<name>.md`.

If the launch instruction says "you are a <name>", "you are an <name>", "you are
the <name>", "act as <name>", or otherwise assigns a noun as your identity, that
is your role. Strip the article and use `<name>` as the role name. Read
`roles/<name>.md` after this file and follow it. Do not ask what your role is
when the role is already stated or inferable from the launch instruction.

If you were not told your role, ask immediately:

```text
What is my role?
```

Available roles are the Markdown files under `roles/`.

## Local Workflow

If `WORKFLOW.md` exists in this AgentWS directory, every agent MUST read it after
reading its role file and before claiming or processing work. Follow
`WORKFLOW.md` for local workflow conventions that are not defined by this
protocol.

`WORKFLOW.md` takes priority over the Default Workflow section below. If
`WORKFLOW.md` conflicts with AgentWS protocol mechanics in this file, follow this
file. If the conflict makes the job ambiguous or unsafe, create a notification
for the responsible coordinating role.

## Default Workflow

Use this workflow when `WORKFLOW.md` is absent or silent on a workflow choice.
If `WORKFLOW.md` gives a different local convention, follow `WORKFLOW.md` unless
it violates this file's protocol mechanics.

Implementation work follows this pipeline:

```text
plan -> code -> review -> commit
                |
                v
         code job for fixes
```

Review is always required after code work. When review requests changes, the
workflow returns to a new code job and repeats until the work is approved or a
blocker requires planner action.

Documentation work follows the handoff defined by the documentation job. When
documentation files change and no stricter handoff is given, the default handoff
is to integration work.

The default quality gate for review is:

1. Code quality: clean, maintainable, and consistent with nearby patterns.
2. Specification adherence: the work does what the original job requested.
3. Verification: required tests/checks ran, or gaps are clearly explained.
4. Documentation: durable facts and user-facing behavior are documented.
5. No regressions: existing behavior is preserved unless the spec says otherwise.
6. Build/integration: the relevant target builds or the failure is explained.

The default review feedback loop is:

1. Reviewer creates a code fix job.
2. Coder picks up the fix job like any other code job.
3. The fix job uses its own branch and worktree.
4. Coder creates a new review job when done.
5. The loop repeats until approved.

The default Git workflow is one branch and one worktree per code job. Branch and
worktree names come from the job spec or `WORKFLOW.md` when provided. If neither
gives names, use the role file's default naming rule.

Use the target project's existing commit message style. If the target has no
clear style, use concise scoped messages such as:

```text
feat(<scope>): add requested behavior
fix(<scope>): correct specific defect
docs(<scope>): document durable technical fact
chore(<scope>): update maintenance artifact
```

The scope is usually the job ID, feature name, subsystem, or document area.
Commit messages must describe the integrated change, not the agent process.

## Continuous Workers

If a role file says the role is a continuous worker, that role MUST run forever
until a human/operator explicitly says to stop.

A continuous worker MUST NOT stop while idle. A continuous worker MUST NOT send a
final/chat response while idle. A continuous worker MUST NOT summarize that there
are no jobs, say it is ready, ask for more work, or return control to the user
because the queue is empty.

While no job/action is available, the next action MUST be the wait command named
by the role file. A tool or harness timeout around `job-wait` is normal idle
behavior, not progress, not failure, and not a signal to diagnose the queue.
After a wait timeout, run the same wait command again. Do not run `job-list`, do
not run `job-claim`, and do not notify the user because of an idle timeout.

If a human/operator explicitly asks a question, answer the question. After
answering, resume the continuous worker loop unless the human/operator explicitly
says to stop, pause, or change roles.

## Job Directory Layout

Each job is a directory under `jobs/`:

```text
jobs/<job-id>/
  spec.md          complete instructions for this job
  type             routing type claimed by a role
  status           pending, claimed, running, done, or failed
  agent.id         identity of the agent that claimed the job
  log.md           append-only progress and decision log
  workspace/       scratch area for job-specific artifacts
```

Use the helper scripts in `bin/` instead of editing queue state files directly.
Direct state-file edits are allowed only when a role file explicitly grants a
queue-recovery exception.

## Statuses

Valid statuses are:

- `pending`: available to be claimed
- `claimed`: locked by an agent but not yet actively processed
- `running`: actively being processed
- `done`: finished successfully
- `failed`: cannot be completed by the current workflow

The normal lifecycle is:

```text
pending -> claimed -> running -> done
                         |
                         v
                       failed
```

No role file or job spec may introduce additional statuses. If a spec or role
instruction uses a word as both a type and a status, the status usage is invalid
unless that word is listed above.

## Job Types

A job's `type` routes it to a role. Types are free-form strings. This protocol
does not define standard types; role files define which types they claim.

Role names and job types are separate identifiers. A role may claim a job type
with the same name, a related name, or a completely different name. The role file
is authoritative for which job type to wait for and claim.

Type and status are independent. A job of any type moves through the normal
statuses: `pending`, `claimed`, `running`, `done`, or `failed`.

Agents MUST claim only jobs of their assigned type unless they were explicitly
assigned a specific job by a human/operator.

## Claiming Work

Continuous workers use the two-step claim flow:

```bash
bin/job-wait -t <type>
bin/job-claim -t <type>
```

`job-wait` may time out after roughly two minutes. That is normal idle behavior.
If it times out, immediately run the same `job-wait` command again. Do not run
`job-claim`, `job-list`, or diagnostic commands after a timeout. Only run
`job-claim` after `job-wait` returns successfully. `job-claim` returns either
`CLAIMED: <job-id>` or `NO_JOBS`.

If assigned a specific job directly:

```bash
bin/job-claim <job-id>
```

After claiming a job:

1. Read `jobs/<job-id>/spec.md`.
2. Read `jobs/<job-id>/log.md` if it has prior entries.
3. Validate that the job is actionable for your role.
4. If actionable, append a start log entry and start it:

```bash
bin/job-start <job-id>
```

One job at a time. Finish, fail, or release the current job before claiming
another.

## Logging

`log.md` is the resumability record. Append structured entries as work proceeds:

```markdown
## <ISO-8601 timestamp> - <short summary>

<what was done, decisions made, outputs produced, commands run, and results>
```

Agents MUST log before completing or failing a job. Agents MUST use
`bin/job-fail <job-id> -m "<reason>"` to mark a job failed and MUST use
`bin/job-done <job-id> -m "<summary>"` to mark a job done. Agents MUST use
`bin/job-release <job-id> -m "<reason>"` to release a job. `bin/job-release`
appends its own release entry, but agents MUST add a fuller log entry first
when the release reason needs context for future agents.

## Creating Jobs

Agents MUST create jobs atomically with complete specs. Always write the spec to
a temporary file first, then pass that file path to `job-create`:

```bash
cat > /tmp/<new-job-id>-spec.md <<'EOF'
# <title>

## Objective
<complete objective with enough explanation for the receiving agent to understand why this job exists>

## Acceptance Criteria
<complete criteria with concrete evidence that proves the job is done>

## When Done
<complete handoff instructions>
EOF
bin/job-create <new-job-id> -t <type> /tmp/<new-job-id>-spec.md
```

Do not create empty/template jobs. Do not run `bin/job-create <id> -t <type>`
without a spec file. Do not create a job and then edit `jobs/<id>/spec.md`; that
creates a race where another agent can claim incomplete work.

## Spec Format

Specs MUST be self-contained enough for the target role to act without guessing.
Specs MUST include extensive explanation, not just terse labels. The receiving
agent needs to understand the reason for the job, what happened before it, why the
requested action matters, what constraints apply, and what exact evidence will
prove completion. Use these sections unless the job has a good reason to add
more:

```markdown
# <short title>

## Target
<repository, directory, service, dataset, or other target, if applicable>

## Objective
<specific work to complete, with enough background to explain why it is needed>

## Context
<dependencies, related jobs, artifacts, prior decisions, and what happened so far>

## Rules
<target-specific docs to follow and job-specific constraints, with any non-obvious reason for the constraint>

## Acceptance Criteria
<how to know the job is complete, including concrete checks or evidence>

## When Done
<exact follow-up work, job IDs, job types, transition command, and the reason for the handoff>
```

The `When Done` section is how AgentWS expresses dependencies. There is no DAG
scheduler. If downstream work is required only after this job, the spec MUST
say exactly which follow-up job to create and when. The explanation MUST be
complete enough that the downstream agent can understand the handoff without
reading the mind of the previous agent.

## Notifications

A notification is a normal AgentWS job whose purpose is to tell another role that
something needs attention. Notifications are not side channels and are not
special files.

The notification job's `type` MUST be the type claimed by the intended receiving
role. The sending role file, current job spec, or local operating convention MUST
make that receiver clear.

Notification job IDs use this form unless the role file or current spec gives a
more specific ID:

```text
notify-<source-job-id>-<short-reason>
```

A notification spec MUST include:

```markdown
# Notification: <short reason>

## Notification Type
<free-form classification, such as completed, blocked, invalid-spec, released, failed, or question>

## Severity
<info | warning | blocker>

## Source Job
<job-id that caused this notification>

## Source Role
<role that created this notification>

## Recipient Role
<role expected to handle this notification>

## Recipient Type
<job type used to route this notification>

## Reason
<what happened, why it matters, and what the sender already tried or observed>

## Action Requested
<what the receiver must decide or do, with enough detail to act without guessing>

## Suggested Follow-Up
<optional concrete job to create, reset, fail, or inspect, including the reason>

## When Done
Complete this notification job with `bin/job-done <job-id> -m "<summary>"` after the action is taken or deliberately declined.
```

Create notification jobs with the same atomic job creation rule as any other job:
write the complete spec first, then call `bin/job-create`. Notification specs
MUST be explanatory enough for the receiving role to reconstruct the problem
from the notification itself.

## Releasing Jobs

Release means: "I claimed this job, but it needs to return to `pending` because it
may be processable later or by another agent of the same type."

Use release for transient or role-local blockers, such as:

- Required dependency is not done yet, but is expected to complete.
- The job was claimed by the wrong role/type due to operator error.
- Required local resources are temporarily unavailable.

Do not use release for a permanently invalid job. Empty specs, template specs,
impossible requirements, missing targets, or contradictory instructions MUST be
marked `failed` after a notification is created for the responsible coordinating
role, unless the role file or current spec gives a concrete recovery path.

Release MUST be performed with:

```bash
bin/job-release <job-id> -m "short reason"
```

If another role needs to act before the job can proceed, the agent MUST create the
notification first, then release the job. This prevents the blocker from being
invisible if another agent immediately claims the job again.

## Problem Handling

Use these global rules unless the role file gives a stricter role-specific rule:

- If the job is actionable but the produced work has issues, create the normal
  follow-up job for those issues. Do not mark the current job failed merely
  because work or validation found problems.
- If the job cannot be processed because the spec is invalid or impossible,
  the agent MUST create a notification for the responsible coordinating role,
  MUST log the blocker, and MUST mark the job failed with
  `bin/job-fail <job-id> -m "<reason>"`.
- If the blocker is temporary and the same job may be valid later, create a
  notification if useful, then release the job with
  `bin/job-release <job-id> -m "<reason>"`.
- If a helper command fails because the queue state is corrupt, log the failure,
  create a notification for the responsible coordinating role if possible, and
  mark the job failed with `bin/job-fail <job-id> -m "<reason>"` if possible.
- Never modify another agent's claimed/running job.

## Status Transitions

Status transitions MUST be performed only through transition helpers. Agents
MUST NOT edit `status` files directly. Each helper checks the current status
before changing anything. Helpers that operate on a claimed or running job also
check that the caller owns the recorded `agent.id`. If the transition is
invalid, the helper MUST exit immediately with a visible error.

| Current Status | New Status | Required Helper | When To Use |
| --- | --- | --- | --- |
| `pending` | `claimed` | `bin/job-claim <job-id>` or `bin/job-claim -t <type>` | Claim available work. |
| `claimed` | `running` | `bin/job-start <job-id>` | Start processing a claimed job after reading the spec and logging the start. |
| `running` | `done` | `bin/job-done <job-id> -m "<summary>"` | Complete successful work after logging results and creating required follow-up jobs. |
| `claimed` | `pending` | `bin/job-release <job-id> -m "<reason>"` | Return a claimed job that may be processable later or by another agent of the same type. |
| `running` | `pending` | `bin/job-release <job-id> -m "<reason>"` | Return a running job that hit a temporary blocker and may be processable later. |
| `claimed` | `failed` | `bin/job-fail <job-id> -m "<reason>"` | Fail a claimed job that cannot be processed by this workflow. |
| `running` | `failed` | `bin/job-fail <job-id> -m "<reason>"` | Fail a running job that cannot be completed by this workflow. |

There is no generic status setter. Do not edit `status` files directly.

## Helpers

The `bin/` directory contains queue helpers:

- `bin/job-create <job-id> -t <type> <spec-file>`: create a job with a complete spec
- `bin/job-wait [-t <type>]`: wait for a pending job
- `bin/job-claim [job-id] [-t <type>]`: claim a pending job
- `bin/job-start <job-id>`: transition a claimed job to running
- `bin/job-done <job-id> -m <message>`: transition a running job to done
- `bin/job-release <job-id> -m <message>`: release a claimed/running job to pending
- `bin/job-fail <job-id> -m <message>`: mark a job failed with a log entry
- `bin/job-list [status]`: list jobs, optionally filtered by status
- `bin/job-mine`: list jobs claimed by the current agent process
- `bin/job-watch <status>`: watch jobs entering a status
- `bin/job-orphans`: list claimed/running jobs whose owning process died
- `bin/job-reap [minutes]`: reset stale claimed/running jobs
- `bin/job-reset-orphans`: reset claimed/running jobs whose owning process died

Use helpers rather than manipulating queue state files directly.

## General Rules

- Follow this protocol first, then your role file, then the job spec and target docs.
- Keep specs complete and concrete.
- Never create empty jobs.
- Never introduce statuses outside the global status set.
- Never claim more than one job at a time.
- Never modify another agent's claimed/running job.
- Always log important decisions.
- Preserve existing job history; logs are append-only.
