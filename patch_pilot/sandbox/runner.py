"""
Isolated sandbox runner for validating code patches against synthesized pytest suites.
"""

import sys
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class TestRunResult:
    """Outcome of a test suite execution in the sandbox."""
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    error_message: Optional[str] = None

    @property
    def feedback_trace(self) -> str:
        """Extracts key failure feedback for the reflection agent."""
        if self.passed:
            return "ALL TESTS PASSED."
        if self.timed_out:
            return f"EXECUTION TIMED OUT: {self.error_message}"
        output = (self.stdout + "\n" + self.stderr).strip()
        # Return the last 50 lines to keep context concise and focused
        lines = output.splitlines()
        return "\n".join(lines[-50:]) if len(lines) > 50 else output


class SandboxRunner:
    """Executes code and test suites in a transient, isolated directory."""

    def __init__(self, timeout_seconds: int = 15):
        self.timeout_seconds = timeout_seconds

    def run_test(
        self,
        source_code: str,
        test_code: str,
        module_name: str = "target_module"
    ) -> TestRunResult:
        """
        Executes pytest in a sandbox with the given source code and test suite.
        """
        with tempfile.TemporaryDirectory(prefix="patchpilot_sandbox_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_file = tmp_path / f"{module_name}.py"
            test_file = tmp_path / "test_target.py"

            source_file.write_text(source_code, encoding="utf-8")
            test_file.write_text(test_code, encoding="utf-8")

            # Run pytest using current python executable
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(test_file.name),
                "-v",
                "--tb=short"
            ]

            start_time = time.time()
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(tmp_path),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                duration = round(time.time() - start_time, 3)
                passed = (proc.returncode == 0)
                return TestRunResult(
                    passed=passed,
                    exit_code=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    duration_seconds=duration,
                    timed_out=False
                )

            except subprocess.TimeoutExpired as e:
                duration = round(time.time() - start_time, 3)
                return TestRunResult(
                    passed=False,
                    exit_code=-1,
                    stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else str(e.stdout or ""),
                    stderr=e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr or ""),
                    duration_seconds=duration,
                    timed_out=True,
                    error_message=f"Process exceeded {self.timeout_seconds}s limit."
                )

            except Exception as e:
                duration = round(time.time() - start_time, 3)
                return TestRunResult(
                    passed=False,
                    exit_code=-2,
                    stdout="",
                    stderr=str(e),
                    duration_seconds=duration,
                    timed_out=False,
                    error_message=f"Failed to launch sandbox: {e}"
                )
