# SPDX-License-Identifier: MIT

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "template"


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def read_int(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0


def read_json_lines(path: Path):
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []


class AgentRunnerCleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.root = self.tmp / "agentws"
        shutil.copytree(TEMPLATE_ROOT, self.root)

        task_dir = self.root / "tasks" / "task-1"
        task_dir.mkdir(parents=True)
        (task_dir / "spec.md").write_text("test task\n", encoding="utf-8")
        (task_dir / "log.md").write_text("", encoding="utf-8")
        (task_dir / "state").write_text("open\n", encoding="utf-8")

        job_dir = self.root / "jobs" / "job-1"
        job_dir.mkdir(parents=True)
        (job_dir / "role").write_text("planner\n", encoding="utf-8")
        (job_dir / "task-id").write_text("task-1\n", encoding="utf-8")
        (job_dir / "spec.md").write_text("test job\n", encoding="utf-8")
        (job_dir / "status").write_text("pending\n", encoding="utf-8")
        (job_dir / "log.md").write_text("", encoding="utf-8")

        fake_bin = self.tmp / "bin"
        fake_bin.mkdir()
        self.fake_pi = fake_bin / "pi"
        self.write_fake_pi(
            "\n".join(
                [
                    "#!/bin/sh",
                    "trap 'exit 0' TERM INT",
                    "while :; do sleep 1; done",
                ]
            )
        )

        self.env = os.environ.copy()
        self.env["PATH"] = f"{fake_bin}{os.pathsep}{self.env.get('PATH', '')}"
        self.env["AGENTWS_WAIT_INTERVAL"] = "1"

    def tearDown(self):
        self.tmpdir.cleanup()

    def write_fake_pi(self, text):
        self.fake_pi.write_text(text, encoding="utf-8")
        self.fake_pi.chmod(0o755)

    def assert_job_released_after_sigterm(self, command):
        proc = subprocess.Popen(
            command,
            cwd=self.root,
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            job_dir = self.root / "jobs" / "job-1"
            self.assertTrue(wait_for(lambda: read_text(job_dir / "status") == "claimed"))
            self.assertEqual(read_text(job_dir / "agent-id"), "agent-1")
            self.assertTrue((job_dir / "lock").is_dir())
            transcript = self.root / "agents" / "agent-1" / "transcript.log"
            self.assertTrue(wait_for(lambda: "run start" in read_text(transcript)))

            proc.send_signal(signal.SIGTERM)
            proc.communicate(timeout=5)

            self.assertEqual(proc.returncode, 128 + signal.SIGTERM)
            self.assertEqual(read_text(job_dir / "status"), "pending")
            self.assertFalse((job_dir / "agent-id").exists())
            self.assertFalse((job_dir / "lock").exists())
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

    def test_non_interactive_agent_releases_job_on_sigterm(self):
        self.assert_job_released_after_sigterm(
            [str(self.root / "tools" / "agent"), "--pi", "--headless", "planner", "agent-1"]
        )

    def test_interactive_agent_releases_job_on_sigterm(self):
        self.assert_job_released_after_sigterm(
            [str(self.root / "tools" / "agent-pi-interactive"), "--headless", "planner", "agent-1"]
        )

    def test_console_idle_messages_start_new_pi_rpc_prompts(self):
        input_log = self.tmp / "pi-input.jsonl"
        self.write_fake_pi(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "import json",
                    "import os",
                    "import sys",
                    "from pathlib import Path",
                    "log = Path(os.environ['PI_INPUT_LOG'])",
                    "for line in sys.stdin:",
                    "    with log.open('a', encoding='utf-8') as stream:",
                    "        stream.write(line)",
                    "        stream.flush()",
                    "    print(json.dumps({'type': 'turn_start'}), flush=True)",
                    "    print(json.dumps({'type': 'turn_end'}), flush=True)",
                    "    print(json.dumps({'type': 'response', 'success': True}), flush=True)",
                ]
            )
        )
        self.env["PI_INPUT_LOG"] = str(input_log)

        proc = subprocess.Popen(
            [str(self.root / "tools" / "agent-pi-interactive"), "--console", "--headless"],
            cwd=self.root,
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            input_fifo = self.root / "agents" / "console" / "input.fifo"
            self.assertTrue(wait_for(input_fifo.exists))

            self.write_interactive_input(input_fifo, "first")
            self.assertTrue(wait_for(lambda: len(read_json_lines(input_log)) >= 1))
            busy_file = self.root / "agents" / "console" / "busy"
            self.assertTrue(wait_for(lambda: read_text(busy_file) == "0"))
            self.write_interactive_input(input_fifo, "second")
            self.assertTrue(wait_for(lambda: len(read_json_lines(input_log)) >= 2))

            sent = read_json_lines(input_log)
            self.assertEqual(["prompt", "prompt"], [item["type"] for item in sent[:2]])
            transcript = self.root / "agents" / "console" / "transcript.log"
            self.assertTrue(wait_for(lambda: read_text(transcript).count("### User") >= 2))
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.communicate(timeout=5)

    def test_console_message_while_streaming_uses_pi_rpc_follow_up(self):
        input_log = self.tmp / "pi-input.jsonl"
        self.write_fake_pi(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "import json",
                    "import os",
                    "import sys",
                    "from pathlib import Path",
                    "log = Path(os.environ['PI_INPUT_LOG'])",
                    "for index, line in enumerate(sys.stdin):",
                    "    with log.open('a', encoding='utf-8') as stream:",
                    "        stream.write(line)",
                    "        stream.flush()",
                    "    if index == 0:",
                    "        print(json.dumps({'type': 'turn_start'}), flush=True)",
                    "    elif index == 1:",
                    "        print(json.dumps({'type': 'turn_end'}), flush=True)",
                    "        print(json.dumps({'type': 'response', 'success': True}), flush=True)",
                ]
            )
        )
        self.env["PI_INPUT_LOG"] = str(input_log)

        proc = subprocess.Popen(
            [str(self.root / "tools" / "agent-pi-interactive"), "--console", "--headless"],
            cwd=self.root,
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            input_fifo = self.root / "agents" / "console" / "input.fifo"
            busy_file = self.root / "agents" / "console" / "busy"
            self.assertTrue(wait_for(input_fifo.exists))

            self.write_interactive_input(input_fifo, "first")
            self.assertTrue(wait_for(lambda: read_text(busy_file) == "1"))
            self.write_interactive_input(input_fifo, "second")
            self.assertTrue(wait_for(lambda: len(read_json_lines(input_log)) >= 2))

            sent = read_json_lines(input_log)
            self.assertEqual(["prompt", "follow_up"], [item["type"] for item in sent[:2]])
            transcript = self.root / "agents" / "console" / "transcript.log"
            self.assertTrue(wait_for(lambda: read_text(transcript).count("### User") >= 2))
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.communicate(timeout=5)

    def write_interactive_input(self, input_fifo: Path, message: str):
        with input_fifo.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps({"message": message, "mode": "prompt"}) + "\n")

    def test_run_agentws_restarts_agent_after_nonzero_exit(self):
        count_file = self.tmp / "pi-starts"
        self.write_fake_pi(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "from pathlib import Path",
                    f"path = Path({str(count_file)!r})",
                    "try:",
                    "    count = int(path.read_text(encoding='utf-8'))",
                    "except (OSError, ValueError):",
                    "    count = 0",
                    "path.write_text(str(count + 1), encoding='utf-8')",
                    "raise SystemExit(7)",
                ]
            )
        )
        team_file = self.tmp / "test.team"
        team_file.write_text("agent-1 planner pi\n", encoding="utf-8")

        proc = subprocess.Popen(
            [str(self.root / "tools" / "run_agentws"), str(team_file)],
            cwd=self.root,
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            self.assertTrue(wait_for(lambda: read_int(count_file) >= 2, timeout=6.0))
            self.assertIsNone(proc.poll())
            status_file = self.root / "agents" / ".team-runs" / "agent-1.last-status"
            self.assertTrue(wait_for(lambda: read_text(status_file) == "7"))
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
