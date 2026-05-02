# AgentWS — Filesystem-Based Job Protocol

You are an agent operating within a shared, filesystem-based job system.
Multiple agents work concurrently on independent jobs. Coordination happens
entirely through files — no database, no server.

AgentWS is **only the queue**. It knows nothing about your project. All
project-specific behavior — code style, testing requirements, review
criteria, workflow rules — lives in the job specs and in the project
repo's own documentation.

## Project-Specific Documentation

**TPA Cleanup Project Workflow**: See `WORKFLOW.md` for the complete pipeline,
execution phases, and quality gates for this project.

## Quick Start — Determine Your Role

**CRITICAL**: You are an agent with a specific role. Your role defines everything you do.

### How to Know Your Role

1. **If someone told you** (examples):
   - "You are a coder" → Your role is `coder`
   - "Be the reviewer" → Your role is `reviewer`
   - "Act as planner" → Your role is `planner`
   - "You are the committer" → Your role is `committer`
   - "Monitor the system" → Your role is `monitor`

2. **If no one told you**: ASK IMMEDIATELY!
   Say: "What is my role? (e.g., coder/reviewer/committer/planner/monitor)"

3. **Once you know your role**:
   - Read `roles/<your-role>.md` for your complete instructions
   - Follow those instructions EXACTLY
   - Work indefinitely - never stop unless your role says to

### Available Roles

Check the `roles/` directory to discover available roles. Common examples include:
- `roles/coder.md` - Implements features, fixes bugs, writes code
- `roles/reviewer.md` - Reviews code, ensures quality, approves/rejects
- `roles/committer.md` - Merges approved code to main branch
- `roles/planner.md` - Decomposes tasks, creates job sequences, writes reports
- `roles/monitor.md` - Watches system health, resets orphaned jobs

More roles may exist - always check what's available in `roles/`.

**Your role file is your complete instruction manual. Follow it precisely.**

### Special Case: "Work on job X"
If assigned a specific job without a role:
1. Run `bin/job-claim <job-id>` to claim it.
2. Read `jobs/<job-id>/spec.md` to understand the task.
3. Run `bin/job-status <job-id> running`.
4. Do the work. Log progress to `jobs/<job-id>/log.md`.
5. When done, follow the **When Done** section in the spec.
6. Set status to `done` (or `review` if the spec says so).

### "You are a <type> agent"
You are a worker for a specific job type. Your role defines your specific responsibilities.

**IMPORTANT**: You must work INDEFINITELY. Never terminate. Keep working forever.

**IDLE OUTPUT GUARDRAIL**: While you are in a continuous worker role and no job/action is available, your only allowed action is another wait/claim/monitoring tool call appropriate for your role. Do not send a final/chat response, do not summarize idle state, do not acknowledge that you are waiting, and do not stop. Producing a final response while idle is a worker failure; the correct next action is always the next wait/claim/monitoring command.

**Check if there's a role document for your type**:
- Look in `roles/<type>.md` for detailed instructions
- Common roles: `planner`, `coder`, `reviewer`, `committer`

If a role document exists, **follow it exactly**. It contains:
- Your specific workflow
- Quality standards
- How to hand off work to the next role
- What to do when things go wrong

**Generic workflow** (if no role document):

Repeat this forever:

1. **Wait for work** (this will block until a job is available):
   ```bash
   bin/job-wait -t <type>
   ```
   If this times out (after ~2 minutes), that's normal - just run it again.
   **CRITICAL**: After a timeout, your next action MUST be another `job-wait` call.
   Never send a message to the user about timeouts or idle state.

2. **Claim a job** (this returns immediately):
   ```bash
   bin/job-claim -t <type>
   ```
   This returns either `CLAIMED: <job-id>` or `NO_JOBS`.

3. **Process the job** if you got one:
   - If output was `CLAIMED: <job-id>`, process that exact job
   - Read `jobs/<job-id>/spec.md` for instructions
   - Log progress to `jobs/<job-id>/log.md`
   - Follow the "When Done" instructions
   - Mark the job done/failed when complete

4. **Return to step 1** - never exit, never stop

**IDLE BEHAVIOR ENFORCEMENT**:
While in this role and waiting for jobs:
- A timeout is NOT progress, NOT failure, and NOT something to report
- The correct response to timeout is another tool call, indefinitely
- Never send a final assistant message during idle waiting
- Never summarize idleness, never say "ready", never return control to user
- The only valid interruption is the user explicitly asking a question or stopping you

**DO NOT:**
- Exit when idle
- Tell the user there are no jobs
- Look for work outside the job system
- Interpret timeouts as errors
- Create complex job-finding logic

**DO:**
- Use job-wait to block until work arrives
- Use job-claim to claim work
- Treat timeouts as normal (just retry)
- Stay in your infinite loop forever
- Trust that jobs will arrive through the system

### "Resume job X"
A previous agent was interrupted.
1. Claim the job. Read `log.md` to see what was already done.
2. Continue from where it left off. Do not redo completed work.

---

## Standard Development Workflow

For software development projects, use this proven workflow:

```
planner → coder → reviewer → committer → [next task]
```

1. **Planner** (`roles/planner.md`)
   - Breaks down high-level goals into concrete tasks
   - Creates numbered sequence of implementation jobs
   - Designs the dependency chain

2. **Coder** (`roles/coder.md`)
   - Claims code jobs
   - Implements in isolated git worktree
   - **MUST build and test successfully**
   - Pushes to feature branch
   - Creates review job

3. **Reviewer** (`roles/reviewer.md`)
   - Reviews code on feature branch
   - Verifies build and tests
   - Creates commit job (if approved) or fix job (if not)

4. **Committer** (`roles/committer.md`)
   - Merges approved branches to main
   - Verifies build still works after merge
   - Creates fix job if integration fails

This workflow ensures:
- Code is always buildable
- Reviews happen before merge
- Integration issues caught immediately
- Clear handoffs between roles

---

## Spec Format

Job specs should be self-contained. An agent should be able to read
`spec.md` and know everything it needs: what to do, where to do it,
what rules to follow, and what to do when finished.

```markdown
# <short title>

## Project
<path to the project repo, if applicable>

## Objective
<what needs to be done — be specific>

## Context
<any references to other jobs, prior work, or background>

## Rules
<project-specific rules, or a pointer to the project's docs>
Example: "Follow conventions in /path/to/project/AGENTS.md"

## Acceptance Criteria
<how to know the work is correct>

## When Done
<what to do after completing the work>
Examples:
- "Set status to done."
- "Create a review job: bin/job-create <id>-review -t review"
- "Create a test job referencing this job's workspace."
```

The **When Done** section is how dependencies are expressed. There is no
DAG scheduler — the workflow is encoded as instructions that agents
follow. The planner designs the chain; each agent just follows its spec.

### Best Practices for Dependency Management and Job Chaining

Real-world usage on large, multi-stage projects showed that vague "When Done"
language often leads to agents losing track of ordering. Follow these patterns
for robust, self-documenting workflows:

- **Use review jobs as quality gates**: Every significant `code` job should
  be followed by a `<job-id>-review` job (type=`review`). The review
  job becomes the explicit hand-off point. Its spec should:
  - Run the full project code review checklist (from the target project's
    `AGENTS.md`).
  - On **PASS**: execute the *exact* `bin/job-create <next-job-id> -t code`
    command to create the subsequent job.
  - On **FAIL**: create a `<job-id>-fix` job (type=`code` or `fix`).

- **Make "When Done" prescriptive**: Use strong, unambiguous language with
  exact job IDs and literal shell commands. Example:

```markdown
## When Done
1. Append findings to `log.md`.
2. Run `bin/job-status <this-job> review`
3. Create the review: `bin/job-create <this-job>-review -t review`
4. **The review job MUST (only if it passes) create the exact next job:**
   `bin/job-create feature-02-auth -t code`
5. **No downstream job may start until this review reaches `done` status.**
```

- Use **consistent numeric prefixes** (`tpa-01-`, `tpa-02-...`) so the
  intended order is obvious.
- Maintain a single **summary/coordinator job** (type=`plan` or `summary`)
  that review jobs update with overall progress.
- During initial planning, refine all specs before agents claim them.
  After a job is claimed, treat `spec.md` as immutable except for critical
  fixes.

This approach turns a collection of independent jobs into a reliable,
self-documenting pipeline while staying purely filesystem-based.

---

## Directory Layout

```
jobs/
  <job-id>/
    spec.md          # What to do. Immutable once created.
    type             # Job type (e.g., code, review, plan). Immutable.
    status           # Single word: pending, claimed, running, review, done, failed
    agent.id         # Identity of the agent that claimed this job
    log.md           # Append-only structured work log
    workspace/       # Scratch area — your working directory for the job
```

## Status Flow

```
pending → claimed → running → review → done
                       ↓         ↓
                     failed    failed
```

- **pending**: Job is available for any agent to claim.
- **claimed**: An agent has locked this job but hasn't started work yet.
- **running**: Work is in progress.
- **review**: Work is complete and awaiting review by a reviewer agent or human.
- **done**: Job finished successfully.
- **failed**: Job failed. Check `log.md` for details.

## Job Types

Each job has a `type` that determines which agent should work on it.
Types are free-form strings. Examples:

- `plan` — decompose a goal into sub-jobs (use your smartest model)
- `code` — implementation tasks
- `review` — code review
- `research` — investigation, analysis
- `test` — writing or running tests

Agents should only claim jobs matching their assigned type.

## Claiming a Job

**Simple two-step approach**:

```bash
bin/job-wait -t <type>    # Block until a job is available
bin/job-claim -t <type>   # Claim the oldest pending job (no waiting)
```

The separated approach is clearer for agents:
1. `job-wait` blocks indefinitely (may timeout after ~2min, just retry)
2. `job-claim` returns immediately with `CLAIMED: <job-id>` or `NO_JOBS`

You can also claim a specific job:
```bash
bin/job-claim <job-id>    # claim a specific job
```

This uses atomic `mkdir` to create a lock — safe even on NFS.

**Never** modify a job you have not claimed.

## Logging

Append structured entries to `log.md` as you make progress. Format:

```markdown
## <ISO-8601 timestamp> — <short summary>

<details of what was done, decisions made, outputs produced>
```

The log is your resumability mechanism. If you are resuming a previously
started job, **always read `log.md` first** to understand what was already
done before continuing.

## Rules

- **One job at a time.** Finish or release your current job before claiming another.
- **Never modify another agent's job.** Only touch jobs you have claimed.
- **Always log before changing status.** Write what you did before marking done/failed.
- **Be idempotent.** If resuming, check what's already done before acting.
- **Keep workspace/ clean.** Final outputs should be clearly identifiable.
- **Follow the spec.** The spec is your contract. Follow its rules and its When Done section.

## Helpers

The `bin/` directory contains shell scripts for job management:

- `bin/job-create <job-id> -t <type> [spec-file]` — Create a new job with a type
  - **IMPORTANT**: Always provide spec-file to avoid race conditions!
  - Without spec-file: Creates job with empty template (agent may claim it prematurely)
  - With spec-file: Creates job atomically with complete specification
- `bin/job-wait [-t <type>]` — Block until a pending job is available
- `bin/job-claim [-t <type>]` — Claim a pending job (returns immediately with CLAIMED: or NO_JOBS)
- `bin/job-list [status]` — List jobs, optionally filtered by status
- `bin/job-status <job-id> [new-status]` — Get or set job status
- `bin/job-watch <status>` — Watch for jobs entering a given status (e.g., `review`)
- `bin/job-reap [minutes]` — Reset stale claimed/running jobs (default: 60 min)

Use these helpers rather than manipulating files directly — they handle
locking and validation.

### Best Practice: Creating Jobs with Complete Specifications

**Always prepare the spec BEFORE creating the job:**

```bash
# GOOD: Write spec first, then create job atomically
cat > /tmp/spec.md <<'EOF'
# Job Specification
## Objective
[Complete objective here]
## Acceptance Criteria
[Complete criteria here]
EOF
bin/job-create my-job -t code /tmp/spec.md

# BAD: Create job then edit (race condition!)
bin/job-create my-job -t code  # Creates with empty template
vim jobs/my-job/spec.md         # Too late - agent might have claimed it!
```
