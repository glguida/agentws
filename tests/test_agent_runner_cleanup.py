# SPDX-License-Identifier: MIT

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
