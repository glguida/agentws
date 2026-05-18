# SPDX-License-Identifier: MIT

import contextlib
import importlib.machinery
import importlib.util
import io
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTWS_PATH = REPO_ROOT / "template" / "tools" / "agentws"


def load_agentws():
    loader = importlib.machinery.SourceFileLoader("agentws_tool", str(AGENTWS_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


AGENTWS = load_agentws()


def read_int(path):
    try:
        return int(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0


def wait_for(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


class ProcessSupervisorTest(unittest.TestCase):
    def test_restarts_exited_process(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            count_file = tmp / "starts"
            worker = tmp / "worker.py"
            worker.write_text(
                "\n".join(
                    [
                        "import sys",
                        "import time",
                        "from pathlib import Path",
                        "path = Path(sys.argv[1])",
                        "try:",
                        "    count = int(path.read_text(encoding='utf-8'))",
                        "except (OSError, ValueError):",
                        "    count = 0",
                        "path.write_text(str(count + 1), encoding='utf-8')",
                        "time.sleep(0.05)",
                    ]
                ),
                encoding="utf-8",
            )

            processes = []

            def start_worker():
                proc = subprocess.Popen(
                    [sys.executable, str(worker), str(count_file)],
                    start_new_session=True,
                )
                processes.append(proc)
                return proc

            supervisor = AGENTWS.ProcessSupervisor(
                "test",
                start_worker,
                check_interval=0.05,
                restart_delay=0.05,
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                try:
                    supervisor.start()
                    self.assertTrue(wait_for(lambda: read_int(count_file) >= 2))
                finally:
                    supervisor.stop()
            self.assertIn("restarting", output.getvalue())
            self.assertIn("restarted", output.getvalue())
            for proc in processes:
                AGENTWS.stop_team(proc)

    def test_stop_team_signals_process_group_after_parent_exit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            pid_file = tmp / "child.pid"
            marker_file = tmp / "terminated"
            child_script = tmp / "child.py"
            parent_script = tmp / "parent.py"

            child_script.write_text(
                "\n".join(
                    [
                        "import os",
                        "import signal",
                        "import sys",
                        "import time",
                        "from pathlib import Path",
                        "pid_path = Path(sys.argv[1])",
                        "marker_path = Path(sys.argv[2])",
                        "def handle_term(_signum, _frame):",
                        "    marker_path.write_text('terminated', encoding='utf-8')",
                        "    raise SystemExit(0)",
                        "signal.signal(signal.SIGTERM, handle_term)",
                        "pid_path.write_text(str(os.getpid()), encoding='utf-8')",
                        "while True:",
                        "    time.sleep(1)",
                    ]
                ),
                encoding="utf-8",
            )
            parent_script.write_text(
                "\n".join(
                    [
                        "import subprocess",
                        "import sys",
                        "import time",
                        "subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2], sys.argv[3]])",
                        "time.sleep(0.1)",
                    ]
                ),
                encoding="utf-8",
            )

            parent = subprocess.Popen(
                [sys.executable, str(parent_script), str(child_script), str(pid_file), str(marker_file)],
                start_new_session=True,
            )
            try:
                parent.wait(timeout=2)
                self.assertTrue(wait_for(pid_file.exists))

                AGENTWS.stop_team(parent)

                self.assertTrue(wait_for(marker_file.exists))
            finally:
                child_pid = read_int(pid_file)
                if child_pid:
                    try:
                        os.kill(child_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass


if __name__ == "__main__":
    unittest.main()
