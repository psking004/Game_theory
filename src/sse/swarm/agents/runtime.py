"""Strategic Systems Engine - Swarm Runtime Supervisor Agent.

Executes and monitors subprocesses inside isolated workspaces, enforcing
strict execution timeouts, capturing telemetry, and preventing socket/process hangs.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from sse.swarm.contracts import ExecutionResult


class RuntimeSupervisorAgent:
    """Sub-agent responsible for process isolation, execution supervision, and telemetry capture."""

    def __init__(self, agent_id: str = "Runtime_01", default_timeout: float = 15.0) -> None:
        self.agent_id = agent_id
        self.default_timeout = default_timeout

    def run_command(
        self,
        command: list[str] | str,
        cwd: Path | str,
        timeout_sec: float | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute command in target workspace with timeout supervision and stdout/stderr capture."""
        timeout = timeout_sec or self.default_timeout
        work_dir = Path(cwd).resolve()

        execution_env = dict(os.environ)
        if env:
            execution_env.update(env)

        # Ensure PYTHONPATH includes workspace root and workspace/src
        src_path = str(work_dir / "src")
        root_path = str(work_dir)
        current_pythonpath = execution_env.get("PYTHONPATH", "")
        execution_env["PYTHONPATH"] = (
            f"{src_path}{os.pathsep}{root_path}{os.pathsep}{current_pythonpath}"
            if current_pythonpath
            else f"{src_path}{os.pathsep}{root_path}"
        )

        t0 = time.perf_counter()
        timed_out = False
        stdout_str = ""
        stderr_str = ""
        exit_code = -1

        try:
            # Execute with pipes to capture output
            process = subprocess.Popen(
                command,
                cwd=str(work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=execution_env,
                shell=False,
            )

            try:
                stdout_str, stderr_str = process.communicate(timeout=timeout)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                stdout_str, stderr_str = process.communicate()
                exit_code = -1
                stderr_str += f"\n[ERROR] Command timed out after {timeout:.2f} seconds."

        except Exception as exc:
            exit_code = -1
            stderr_str = f"Subprocess spawning error: {exc}"

        duration_ms = (time.perf_counter() - t0) * 1000.0

        return ExecutionResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            duration_ms=round(duration_ms, 2),
            timed_out=timed_out,
        )
