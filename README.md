# AgentWS (Agent Workspace)

A git-friendly, human-readable, agent-native workspace for coordinating AI agents. No database, no server, no
framework — just directories, files, and bash.

AgentWS lets multiple AI agents work concurrently on independent jobs,
coordinating entirely through the filesystem. It works on local disks,
NFS, sshfs, or any shared mount.

## TL;DR for Humans

AgentWS is a tiny way to give AI agents durable, project-specific roles without
running a server or adopting a framework.

- **Roles are customizable.** Start with planner, coder, reviewer, and
  committer, then edit them or add your own roles for your project.
- **Roles live in git as Markdown.** The instructions are ordinary `.md` files
  in `roles/`, so they can be reviewed, versioned, branched, and changed with
  the rest of the repo.
- **Agents are easy to launch.** Start an agent with the role you want, for
  example:

```bash
pi "You are a coder"
```

The agent reads the matching role file, claims jobs from the filesystem queue,
logs what it did, and hands work to the next role.

### How to install in your project

To add AgentWS to an existing repository, open an agent in that repository and
point it at the AgentWS repo:

```text
Install AgentWS in this repository using https://github.com/glguida/agentws.
Read the AgentWS README, create an agentws/ directory from the template,
initialize it, and commit the reusable configuration.

Add agentws/jobs/ to this project's .gitignore so runtime jobs are not
committed.
```

This gives your project a committed `agentws/` directory with `AGENTS.md`,
`roles/`, and `bin/`, while keeping runtime job state out of git.

The standard roles are:

- `planner` - breaks goals into concrete jobs
- `coder` - implements code changes
- `reviewer` - reviews completed code
- `committer` - merges approved work

After that, customize the role files in `agentws/roles/` like any other project
documentation, then launch agents with prompts like:

```bash
cd agentws
pi "You are a planner"
pi "You are a coder"
pi "You are a reviewer"
pi "You are a committer"
```

## TL;DR for Agents

**If you're an AI agent being asked to use agentws:**

1. **Set it up** (if not already done):
```bash
git clone https://github.com/glguida/agentws.git
cp -r agentws/template/ ./agentws/
cd agentws/
bin/job-init
```

2. **Create your first job**:
```bash
bin/job-create initial-task -t plan
# Edit jobs/initial-task/spec.md with the goal
```

3. **Launch agents** (tell your human to launch these):
```bash
# Planner to break down the task
pi "You are a planner"

# Coders to implement
pi "You are a coder"

# Reviewer to check quality
pi "You are a reviewer"

# Committer to merge approved code
pi "You are a committer"
```

That's it. The planner breaks your goal into sub-jobs, workers pick
them up as they appear, and the chain flows through the queue.

## Roles

The template includes standard development roles in `template/roles/`:

- **planner.md** - Breaks down goals into concrete tasks
- **coder.md** - Implements features in git branches, must build
- **reviewer.md** - Reviews code quality, doesn't merge
- **committer.md** - Merges approved code, verifies integration

Humans launch agents with the role name:
```bash
pi "You are a coder"
```

The agent will read the matching role document. If you are an agent reading
this, do not launch other agents yourself; tell your human which roles to
launch. Projects can customize these roles or add new ones. The role documents
contain the detailed workflows, quality standards, and handoff procedures.

## Why

Modern multi-agent frameworks (CrewAI, AutoGen, LangGraph) run agents
in-process. They're tightly coupled, hard to resume, and tied to a
specific runtime. If the process dies, the work is lost.

AgentWS (Agent Workspace) takes a different approach:

- **Agents are independent processes.** Each agent is a separate CLI
  session (pi.dev, claude, cursor — anything that reads `AGENTS.md`).
  They don't share memory. They coordinate through files.

- **Everything is inspectable.** `cat jobs/foo/status` tells you the
  state. `cat jobs/foo/log.md` tells you what happened. No dashboards,
  no APIs — just `ls` and `cat`.

- **Work survives crashes.** If an agent dies, the job stays on disk.
  Another agent can pick it up and resume from the log. A reaper script
  reclaims stale jobs automatically.

- **Works anywhere files work.** Local disk, NFS, sshfs, Dropbox, a USB
  stick. No ports to open, no services to run.

- **Role routing via job types.** Run as many planners, coders, reviewers,
  and committers as you need. Each agent claims only jobs matching its role.

- **Dependencies without a DAG engine.** The planner encodes workflow as
  natural language in each job's spec: "When done, create a review job."
  No scheduler, no graph — agents just follow their instructions.

## How It Works

```
jobs/
  my-feature/
    spec.md        # What to do (immutable)
    type           # Job type: plan, code, review, test, ...
    status         # pending → claimed → running → review → done
    agent.id       # Who claimed it
    log.md         # Append-only work log
    workspace/     # Scratch area
```

1. A human (or agent) creates a job with `bin/job-create`.
2. An agent claims it with `bin/job-claim` (atomic `mkdir` lock — NFS-safe).
3. The agent reads `spec.md`, does the work, logs to `log.md`.
4. The agent follows the spec's "When Done" section — maybe mark done,
   maybe create a follow-up job for another agent.

## Setup

### 1. Get agentws

```bash
git clone https://github.com/glguida/agentws.git
```

### 2. Copy the template into your project

```bash
cp -r agentws/template/ /path/to/my-project/agentws/
cd /path/to/my-project/agentws/
bin/job-init
```

### 3. Add jobs/ to your project's .gitignore

```bash
cd /path/to/my-project/
echo "agentws/jobs/" >> .gitignore
```

### 4. Commit the configuration (but not the runtime state)

```bash
git add .gitignore
git add agentws/         # Add all agentws configuration
git commit -m "Add agentws for multi-agent coordination"
```

That's it. Your project now has:

```
my-project/
  .gitignore        # Must include "agentws/jobs/"
  agentws/          # The agent workspace (commit this!)
    AGENTS.md      # Protocol spec — agents read this automatically
    roles/          # Role specifications (planner, coder, reviewer, etc.)
    bin/            # Helper scripts
    jobs/           # Job directories appear here (gitignored)
  src/              # Your actual code
  AGENTS.md         # Your project's own conventions (optional)
```

**Important**: The `agentws/` configuration should be committed to your project's
git repository. This ensures all team members and agents use the same workflow
definitions. Only the `jobs/` directory (runtime state) is gitignored.

Agents launched inside `my-project/agentws/` will automatically read
`AGENTS.md` and understand the job protocol. Your project's own
`AGENTS.md` (if you have one) stays separate — job specs can reference
it for project-specific rules.

### Why commit the configuration?

Committing `agentws/` configuration to git provides:
- **Consistency**: All team members use the same agent roles and workflows
- **Versioning**: Track changes to your agent coordination patterns
- **Customization**: Project-specific role definitions evolve with your code
- **Reproducibility**: New team members can clone and immediately use the same setup

The `jobs/` directory remains gitignored because it contains ephemeral runtime
state that's specific to each work session.

### Alternative: shared directory on NFS/sshfs

If your agents run on different machines, mount a shared directory and
set up agentws there:

```bash
cp -r agentws/template/ /mnt/shared/agentws/
cd /mnt/shared/agentws/
bin/job-init
```

All agents on all machines point to the same `/mnt/shared/agentws/`.
The `mkdir`-based locking works correctly on NFS.

## Quickstart

### 1. Create a seed job

```bash
cd my-project/agentws
bin/job-create add-auth -t plan
```

Edit the spec with your goal:

```bash
$EDITOR jobs/add-auth/spec.md
```

```markdown
# Add OAuth2 authentication

## Project
/path/to/my-project

## Objective
Add Google OAuth2 login to the web app. Users should be able to sign in
with their Google account and have a session persisted in a cookie.

## Rules
Follow conventions in /path/to/my-project/AGENTS.md

## When Done
Set status to done.
```

### 2. Tell your human to launch agents

```bash
# Tell your human to launch agents for different roles
pi "You are a planner"
pi "You are a coder"
pi "You are a reviewer"
pi "You are a committer"
```

Agents will:
- Read their role document for specific instructions
- Claim jobs matching their type
- Follow the workflow defined in their role
- Create follow-up jobs as specified

The specific workflow depends on your project, but the template includes
standard software development roles (planner → coder → reviewer → committer).

### 3. Check job status

```bash
bin/job-list              # See all jobs
bin/job-list running      # See what's in progress
bin/job-list done         # See completed work
```

### 4. Handle stale jobs

If an agent dies mid-work:

```bash
bin/job-reap 60           # Reset jobs stale for >60 minutes to pending
```

## Helpers Reference

| Command | Description |
|---|---|
| `bin/job-init` | Initialize the jobs/ directory |
| `bin/job-create <id> -t <type>` | Create a new job |
| `bin/job-claim [-t <type>] [--wait]` | Claim a pending job (blocks with `--wait`) |
| `bin/job-list [status]` | List jobs, optionally filtered |
| `bin/job-status <id> [status]` | Get or set job status |
| `bin/job-watch <status>` | Watch for jobs entering a status |
| `bin/job-reap [minutes]` | Reclaim stale jobs (default: 60 min) |

## Typical Workflow

```
You (human)
  │
  ├─ Create initial job(s) with your goal
  │
  └─ Launch agents for different roles
       │
       ├─ Each agent claims jobs of its type
       ├─ Does the work according to its role
       ├─ Creates follow-up jobs as specified
       └─ Continues until no more jobs

The template includes standard development roles:
- planner: decomposes goals into tasks
- coder: implements in isolated branches
- reviewer: ensures quality
- committer: merges to main

See template/roles/ for role specifications.
```

### Workflow Chaining Best Practices (Updated)

Real-world usage on complex, multi-stage projects showed that loose or vague
dependency language in specs can cause agents to lose track of ordering.

**Key pattern**: Use `*-review` jobs as explicit quality gates. Each review job
is responsible for running the full checklist **and** creating the next job in
the sequence using an exact `bin/job-create` command.

See the **"Best Practices for Dependency Management and Job Chaining"** section
in `template/AGENTS.md` (and in every copied `AGENTS.md`) for detailed guidance,
prescriptive language examples, and recommended "MUST" rules to use in `When Done`
sections.

This makes even very complex workflows reliable and self-documenting when many
agents run concurrently.

## Design Decisions

**Why filesystem, not SQLite?**
SQLite locking doesn't work reliably on NFS. `mkdir` is atomic on every
filesystem that matters. The filesystem is also universally inspectable —
no special tools needed.

**Why no DAG scheduler?**
Dependencies are encoded as natural language in the "When Done" section
of each spec. The planner designs the chain; agents just follow
instructions. This is simpler, more flexible, and lets you express
conditional logic ("if tests fail, create a fix job") without a graph
DSL.

**Why job types instead of agent names?**
Types decouple the work from the worker. You can run 5 coder agents or one —
the system doesn't care. Scale by adding agents, not by reconfiguring the
queue.

**Why polling in job-claim?**
`fswatch`/`inotify` don't fire on NFS/sshfs (the local kernel never
sees remote writes). Polling with a short interval is simple and
universally reliable. For local disks, `job-watch` uses `fswatch` when
available.

## Requirements

- bash 4+ (for associative arrays in `job-watch`)
- Standard Unix tools: `mkdir`, `cat`, `ls`, `stat`, `date`
- Optional: `fswatch` for real-time file watching on local disks

## License

Public domain. Use it however you want.
