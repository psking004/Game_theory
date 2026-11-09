"""Strategic Systems Engine - Sub-Agent Workspace Sandbox & Privilege Scrubber.

Enforces zero host credential leakage, strict directory confinement with path-traversal
defense, and resource-bounded execution to protect the host against rogue agent behaviors.
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import time
from pathlib import Path

from sse.swarm.contracts import ExecutionResult

# Sensitive environment variable patterns to scrub from sub-agent processes
SENSITIVE_ENV_PATTERNS = [
    re.compile(r".*(?:KEY|TOKEN|SECRET|AUTH|PASS|PASSWORD|CREDENTIAL|PRIVATE).*", re.IGNORECASE),
]

# Explicit safe environment variable allowlist
SAFE_ENV_ALLOWLIST = {
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "PYTHONPATH",
    "LANG",
    "LC_ALL",
    "USERPROFILE",
    "HOME",
    "WINDIR",
    "COMSPEC",
    "SHELL",
    "TERM",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PROCESSOR_ARCHITECTURE",
}


def get_sanitized_environment(extra_env: dict[str, str] | None = None) -> dict[str, str]:
    """Extract a host-scrubbed environment dictionary preventing credential leakage.

    Only passes explicitly allowlisted environment variables, scrubs any variable
    matching sensitive patterns (keys, tokens, credentials), and sets
    PYTHONDONTWRITEBYTECODE=1 to prevent host disk pollution.
    """
    clean_env: dict[str, str] = {}

    for k, v in os.environ.items():
        k_upper = k.upper()
        # Must be in allowlist
        if k_upper in SAFE_ENV_ALLOWLIST:
            # Must not match sensitive pattern (extra guard)
            if not any(pattern.match(k) for pattern in SENSITIVE_ENV_PATTERNS):
                clean_env[k] = v

    # Add extra caller-provided environment variables if non-sensitive
    if extra_env:
        for k, v in extra_env.items():
            if not any(pattern.match(k) for pattern in SENSITIVE_ENV_PATTERNS):
                clean_env[k] = str(v)

    # Hardened standard flags
    clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
    return clean_env


class SandboxedWorkspaceGuard:
    """Directory confinement guard enforcing strict path containment within a sandbox root."""

    def __init__(self, sandbox_root: Path | str) -> None:
        self.sandbox_root = Path(sandbox_root).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def is_path_safe(self, target: Path | str) -> bool:
        """Check whether a target path is safely contained inside the sandbox root."""
        try:
            self.resolve_safe_path(target)
            return True
        except (PermissionError, ValueError):
            return False

    def resolve_safe_path(self, relative_path: Path | str) -> Path:
        """Resolve a file path and verify that it strictly remains inside the sandbox root.

        Raises:
            PermissionError: If path traversal or escape outside sandbox_root is detected.
        """
        raw_str = str(relative_path).strip()
        if not raw_str:
            raise PermissionError("Access denied: empty path provided.")

        # Check for obvious traversal tokens before path resolution
        norm = raw_str.replace("\\", "/")
        parts = norm.split("/")
        if ".." in parts:
            # Preliminary check: inspect if traversing above root
            resolved_candidate = (self.sandbox_root / raw_str).resolve()
            try:
                resolved_candidate.relative_to(self.sandbox_root)
            except ValueError:
                raise PermissionError(
                    f"Path traversal exploit blocked: '{raw_str}' escapes sandbox '{self.sandbox_root}'"
                ) from None

        # Check for absolute path injections attempting to escape sandbox_root
        candidate = Path(raw_str)
        if candidate.is_absolute():
            resolved_candidate = candidate.resolve()
        else:
            resolved_candidate = (self.sandbox_root / candidate).resolve()

        # Strict containment verification
        try:
            resolved_candidate.relative_to(self.sandbox_root)
        except ValueError:
            raise PermissionError(
                f"Path traversal escape denied: '{raw_str}' resolves to outside directory '{resolved_candidate}'"
            ) from None

        # Symlink escape verification: if path exists and is symlink, its target must be within sandbox
        if resolved_candidate.is_symlink():
            real_target = resolved_candidate.resolve()
            try:
                real_target.relative_to(self.sandbox_root)
            except ValueError:
                raise PermissionError(
                    f"Symlink redirection exploit blocked: '{raw_str}' targets outside sandbox '{real_target}'"
                ) from None

        return resolved_candidate

    def safe_write(self, relative_path: str, content: str | bytes, executable: bool = False) -> Path:
        """Safely write content to a file strictly confined within the sandbox."""
        safe_path = self.resolve_safe_path(relative_path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, bytes):
            safe_path.write_bytes(content)
        else:
            safe_path.write_text(content, encoding="utf-8")

        if executable and hasattr(safe_path, "chmod"):
            with contextlib.suppress(OSError):
                safe_path.chmod(0o755)

        return safe_path

    def safe_read(self, relative_path: str) -> str:
        """Safely read content from a file strictly confined within the sandbox."""
        safe_path = self.resolve_safe_path(relative_path)
        if not safe_path.is_file():
            raise FileNotFoundError(f"Safe read failed: file '{safe_path}' does not exist.")
        return safe_path.read_text(encoding="utf-8")


class HardenedProcessExecutor:
    """Supervised subprocess execution runner with resource limits and buffer bounds."""

    def __init__(
        self,
        guard: SandboxedWorkspaceGuard,
        default_timeout_sec: float = 15.0,
        max_output_bytes: int = 100_000,
    ) -> None:
        self.guard = guard
        self.default_timeout_sec = float(default_timeout_sec)
        self.max_output_bytes = int(max_output_bytes)

    def run_command(
        self,
        command: list[str] | str,
        cwd_relative: str = ".",
        timeout_sec: float | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute command in sandbox with sanitized env, timeout, and capture bounds."""
        timeout = float(timeout_sec) if timeout_sec is not None else self.default_timeout_sec
        work_dir = self.guard.resolve_safe_path(cwd_relative)

        # Setup scrubbed environment
        execution_env = get_sanitized_environment(extra_env=extra_env)

        # Ensure PYTHONPATH includes workspace root and workspace/src
        src_dir = work_dir / "src"
        if src_dir.exists():
            current_pp = execution_env.get("PYTHONPATH", "")
            execution_env["PYTHONPATH"] = (
                f"{src_dir}{os.pathsep}{work_dir}{os.pathsep}{current_pp}"
                if current_pp
                else f"{src_dir}{os.pathsep}{work_dir}"
            )

        t0 = time.perf_counter()
        timed_out = False
        stdout_str = ""
        stderr_str = ""
        exit_code = -1

        try:
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

        # Enforce maximum capture bounds to prevent memory denial-of-service
        if len(stdout_str) > self.max_output_bytes:
            stdout_str = (
                stdout_str[: self.max_output_bytes]
                + f"\n... [TRUNCATED: Output exceeded buffer limit of {self.max_output_bytes} bytes]"
            )

        if len(stderr_str) > self.max_output_bytes:
            stderr_str = (
                stderr_str[: self.max_output_bytes]
                + f"\n... [TRUNCATED: Stderr exceeded buffer limit of {self.max_output_bytes} bytes]"
            )

        return ExecutionResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            duration_ms=round(duration_ms, 2),
            timed_out=timed_out,
        )
