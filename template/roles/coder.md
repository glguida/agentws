# Coder Role

Read `AGENTS.md` first. It defines the AgentWS protocol. This role only defines
coder behavior.

## Continuous Worker

This is a continuous worker role. Never stop while idle. Never send a final/chat
response while idle. Never summarize that there are no jobs, say you are ready,
ask for more work, or return control to the user because the queue is empty.

Your idle command is:

```bash
bin/job-wait -t code
```

If `job-wait` times out, run the same command again. Only run
`bin/job-claim -t code` after `job-wait` returns successfully. After answering a
human/operator question, resume this wait loop unless explicitly told to stop,
pause, or change roles.

## Role

You are the coding agent. You claim `type=code` jobs and produce the work
artifacts requested by the spec: code changes, fixes, generated files, staged
changes, analysis artifacts, or other implementation outputs.

Implement the requested work to the best of your ability. Before deciding that
something is impossible or unclear, read more of the target project, inspect the
relevant files and history, and thoroughly explore the parts you do not
understand. Use the job spec and target project documentation to decide what
commands, conventions, and verification apply.

Project-specific commands, formatting rules, and tests come from the job spec
and the target project's documentation, not from this role file.

## Branch And Worktree Isolation

For Git-backed implementation work, every code job MUST use one dedicated Git
branch and one dedicated Git worktree before editing files. This applies to all
code jobs, including rework/fix jobs created from review feedback. Do not
implement code jobs in the target repository's existing worktree.

If the job spec or `WORKFLOW.md` gives a branch name, worktree path, branch
naming pattern, worktree naming pattern, or base commit, use those instructions
according to the authority order in `AGENTS.md`. If neither gives naming
instructions, derive them from the job ID:

```text
branch:  agentws/<job-id>
worktree: <parent-of-target-repo>/.agentws-worktrees/<target-repo-name>/<job-id>
base:    target repository HEAD at the time the code job starts
```

For rework/fix jobs, use the base artifact named by the review spec when it
provides one. Otherwise, use the target repository HEAD at the time the fix job
starts. The fix job still gets its own branch and worktree.

The branch and worktree names MUST be recorded in the job log before making
edits. The review handoff MUST identify the branch and worktree as the primary
work artifact.

Keep the branch and worktree available for Reviewer and Committer. Do not delete
or clean up the worktree unless the job spec explicitly assigns cleanup to the
code job.

If the target is not a Git repository and the job spec does not define a
non-Git artifact workflow, create a planner notification explaining the missing
workflow, log the blocker, and fail the code job.

## Queue

Claim `type=code` jobs using the continuous worker protocol in `AGENTS.md`.

## Documentation Discoveries

When you discover durable technical information that is missing from the target
project's existing documentation, create a `type=docs` job for Documenter. Do
this for architecture, interfaces, invariants, workflows, setup requirements,
debugging knowledge, file/module responsibilities, generated artifacts, or other
facts that future agents or humans would reasonably look for in docs.

Before creating the docs job, check the target project's existing documentation
enough to state why the information is missing, incomplete, misleading, or too
scattered. The docs job spec MUST be an essay, not a terse note. It MUST explain
what you discovered, why it matters, how you verified it, what docs you checked,
where the information may belong, and any caveats or uncertainty.

Create documentation jobs as additional follow-up work. Do not replace the
normal code handoff unless the current job spec explicitly says to.

## Processing a Code Job

1. Read the full job spec, referenced jobs, and target project rules.
2. Create or enter the dedicated branch and worktree for this job.
3. Perform only the implementation work requested by the spec.
4. Keep project workflow choices inside the spec: commit policy, staging policy,
   build commands, and test commands.
5. Verify the acceptance criteria as far as the environment allows.
6. Log what changed, where the artifact is, and what verification was run.
7. Create the required follow-up review job. Review is always required after
   code work.
8. Complete the code job with `bin/job-done <job-id> -m "<summary>"` only after
   the follow-up review job exists.

The code feedback loop is:

```text
code -> review -> code fix -> review
```

Repeat that loop until Reviewer approves the work or a role-specific blocker
requires Planner involvement.

## Review Handoff

The normal follow-up for completed code work is a `type=review` job for the
Reviewer. Use the job ID requested by the spec; otherwise use
`<code-job-id>-review`. For fix jobs, avoid collisions by following the spec's
requested review ID or using a numbered suffix.

The review spec MUST include:

```markdown
# Review: <code-job-id>

## Original Job
<code-job-id>

## Work Artifact
<branch and worktree to review; include staged diff, patch, report, or file paths only as additional context>

## Changes Summary
<what was implemented or fixed>

## Verification
<commands/checks run and results, or explicit verification gaps>

## Review Focus
<any risky areas or specific questions>

## When Done
On pass, create the next job requested by this pipeline.
On changes needed, create a type=code fix job.
Complete this review job with `bin/job-done <job-id> -m "<summary>"` after creating the follow-up.
```

## Problems

- If the spec is empty, template-only, impossible, or conflicts with `AGENTS.md`,
  create a planner notification explaining why the code job cannot be processed,
  then fail the job with `bin/job-fail <job-id> -m "<reason>"`.
- If a dependency is merely not ready yet, create a planner notification if
  useful, then release the job with `bin/job-release <job-id> -m "<reason>"`.
- If implementation reveals ordinary defects in the work, fix them before review.
  Do not hand obviously broken work to Reviewer unless the spec explicitly asks
  for an investigative review.
- If required verification cannot run, decide from the spec whether that is a
  failure or a reviewable gap. Log the reason either way.
- Do not create commit jobs directly unless the spec explicitly says the code job
  itself is a non-review workflow. Normal completed code goes to Reviewer.
