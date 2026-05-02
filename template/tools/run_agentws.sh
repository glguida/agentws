#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: agentws/tools/run_agentws.sh [-n] [-m model] [-c config] [session-name]

Start an AgentWS tmux session from the current Git repository.

Each configured agent starts in ./agentws and runs pi with:
  "You are a <role>"

Options:
  -c config   Agent config file path. Default: <git-root>/agentws/default.team.
  -m model    Pass --model model to every pi agent.
  -n          Create the session without attaching.
  -h          Show this help.

Config format:
  # comments, inline comments, and blank lines are ignored
  coder-1 coder  # window name, role

Examples:
  agentws/tools/run_agentws.sh
  agentws/tools/run_agentws.sh -m sonnet
  agentws/tools/run_agentws.sh -n -m opus -c /tmp/team tpa-agents
EOF
}

CONFIG_FILE=""
NO_ATTACH=0
MODEL=""

while getopts ":hc:m:n" opt; do
    case "$opt" in
        h)
            usage
            exit 0
            ;;
        c)
            CONFIG_FILE="$OPTARG"
            ;;
        m)
            MODEL="$OPTARG"
            ;;
        n)
            NO_ATTACH=1
            ;;
        :)
            echo "error: option -$OPTARG requires an argument" >&2
            usage >&2
            exit 2
            ;;
        \?)
            echo "error: unknown option: -$OPTARG" >&2
            usage >&2
            exit 2
            ;;
    esac
done
shift $((OPTIND - 1))

if [ "$#" -gt 1 ]; then
    echo "error: expected at most one session name" >&2
    usage >&2
    exit 2
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
    echo "error: run this from inside a Git repository" >&2
    exit 1
fi

AGENTWS_DIR="$REPO_ROOT/agentws"
if [ -z "$CONFIG_FILE" ]; then
    CONFIG_FILE="$AGENTWS_DIR/default.team"
fi
SESSION_NAME="${1:-agentws-demo}"

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: required command not found: $1" >&2
        exit 1
    fi
}

shell_quote() {
    printf "%q" "$1"
}

read_json_config() {
    local config="$1"

    require_command python3
    python3 - "$config" <<'PY'
import json
import sys

path = sys.argv[1]

try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except OSError as e:
    print(f"error: cannot read config {path}: {e}", file=sys.stderr)
    sys.exit(2)
except json.JSONDecodeError as e:
    print(f"error: invalid JSON in {path}: {e}", file=sys.stderr)
    sys.exit(2)

if isinstance(data, dict):
    data = data.get("agents")

if not isinstance(data, list):
    print("error: JSON config must be a list or an object with an agents list", file=sys.stderr)
    sys.exit(2)

for i, agent in enumerate(data, 1):
    if not isinstance(agent, dict):
        print(f"error: agent #{i} must be an object", file=sys.stderr)
        sys.exit(2)

    name = agent.get("name")
    role = agent.get("role")
    if not isinstance(name, str) or not name:
        print(f"error: agent #{i} has no name", file=sys.stderr)
        sys.exit(2)
    if not isinstance(role, str) or not role:
        print(f"error: agent {name} has no role", file=sys.stderr)
        sys.exit(2)
    if any(ch in name for ch in "\t\r\n"):
        print(f"error: agent {name!r} contains unsupported whitespace", file=sys.stderr)
        sys.exit(2)
    if any(ch in role for ch in "\t\r\n"):
        print(f"error: role for agent {name} contains unsupported whitespace", file=sys.stderr)
        sys.exit(2)

    print(f"{name}\t{role}")
PY
}

read_text_config() {
    local config="$1"

    awk '
        { sub(/#.*/, "") }
        /^[[:space:]]*($|#)/ { next }
        NF != 2 {
            printf("error: %s:%d: expected: <name> <role>\n", FILENAME, FNR) > "/dev/stderr"
            exit 2
        }
        { printf("%s\t%s\n", $1, $2) }
    ' "$config"
}

read_agent_config() {
    local config="$1"

    case "$config" in
        *.json)
            read_json_config "$config"
            ;;
        *)
            read_text_config "$config"
            ;;
    esac
}

validate_agent() {
    local name="$1"
    local role="$2"

    if [[ ! "$name" =~ ^[A-Za-z0-9_.-]+$ ]]; then
        echo "error: invalid agent name '$name' (use letters, numbers, _, ., -)" >&2
        exit 2
    fi
    if [[ ! "$role" =~ ^[A-Za-z0-9_.-]+$ ]]; then
        echo "error: invalid role '$role' for agent '$name' (use letters, numbers, _, ., -)" >&2
        exit 2
    fi
}

agent_prompt() {
    printf "You are a %s" "$1"
}

pi_shell_command() {
    local prompt="$1"

    if [ -n "$MODEL" ]; then
        printf "pi --model %s %s" "$(shell_quote "$MODEL")" "$(shell_quote "$prompt")"
    else
        printf "pi %s" "$(shell_quote "$prompt")"
    fi
}

start_agent_window() {
    local window="$1"
    local role="$2"
    local target="$SESSION_NAME:$window"

    validate_agent "$window" "$role"
    tmux new-window -t "$SESSION_NAME:" -n "$window" -c "$AGENTWS_DIR"
    tmux send-keys -t "$target" "$(pi_shell_command "$(agent_prompt "$role")")" C-m
}

if [ ! -d "$AGENTWS_DIR" ]; then
    echo "error: AgentWS directory not found: $AGENTWS_DIR" >&2
    exit 1
fi
if [ ! -f "$CONFIG_FILE" ]; then
    echo "error: agent config not found: $CONFIG_FILE" >&2
    exit 1
fi

require_command tmux
require_command pi

CONFIG_LINES="$(read_agent_config "$CONFIG_FILE")"
if [ -z "$CONFIG_LINES" ]; then
    echo "error: agent config contains no agents: $CONFIG_FILE" >&2
    exit 2
fi
mapfile -t AGENT_ROWS <<< "$CONFIG_LINES"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "tmux session already exists: $SESSION_NAME"
    if [ "$NO_ATTACH" = "1" ]; then
        exit 0
    fi
    exec tmux attach-session -t "$SESSION_NAME"
fi

FIRST_ROW="${AGENT_ROWS[0]}"
FIRST_NAME="${FIRST_ROW%%$'\t'*}"
FIRST_ROLE="${FIRST_ROW#*$'\t'}"
validate_agent "$FIRST_NAME" "$FIRST_ROLE"

tmux new-session -d -s "$SESSION_NAME" -n "$FIRST_NAME" -c "$AGENTWS_DIR"
tmux send-keys -t "$SESSION_NAME:$FIRST_NAME" \
    "$(pi_shell_command "$(agent_prompt "$FIRST_ROLE")")" C-m

for row in "${AGENT_ROWS[@]:1}"; do
    agent_name="${row%%$'\t'*}"
    agent_role="${row#*$'\t'}"
    start_agent_window "$agent_name" "$agent_role"
done

tmux select-window -t "$SESSION_NAME:$FIRST_NAME"

echo "Started tmux session '$SESSION_NAME' in $AGENTWS_DIR"
echo "Agent config: $CONFIG_FILE"
echo "Attach with: tmux attach-session -t $SESSION_NAME"

if [ "$NO_ATTACH" != "1" ]; then
    exec tmux attach-session -t "$SESSION_NAME"
fi
