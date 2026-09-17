"""
Unit tests for the Sandbox execution runner.
"""

from patch_pilot.sandbox.runner import SandboxRunner


def test_sandbox_passing_execution():
    runner = SandboxRunner(timeout_seconds=10)
    source = "def add(a, b):\n    return a + b\n"
    test_code = "from target_module import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"

    result = runner.run_test(source, test_code)
    assert result.passed is True
    assert result.exit_code == 0
    assert "ALL TESTS PASSED" in result.feedback_trace


def test_sandbox_failing_execution():
    runner = SandboxRunner(timeout_seconds=10)
    source = "def add(a, b):\n    return a - b\n"  # Intentional bug
    test_code = "from target_module import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"

    result = runner.run_test(source, test_code)
    assert result.passed is False
    assert result.exit_code != 0
    assert "assert" in result.feedback_trace.lower() or "failed" in result.feedback_trace.lower()


def test_sandbox_timeout_handling():
    runner = SandboxRunner(timeout_seconds=2)
    source = "import time\ndef hang():\n    time.sleep(10)\n"
    test_code = "from target_module import hang\n\ndef test_hang():\n    hang()\n"

    result = runner.run_test(source, test_code)
    assert result.passed is False
    assert result.timed_out is True
    assert "limit" in (result.error_message or "").lower()
