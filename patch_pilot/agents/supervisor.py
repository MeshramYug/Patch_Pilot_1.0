"""
Supervisor Orchestrator Agent.
Coordinates AST inspection, multi-agent committee, sandbox execution, and self-healing.
"""

from typing import Callable, Optional
from patch_pilot.ast_engine.inspector import CodeInspector
from patch_pilot.sandbox.runner import SandboxRunner
from patch_pilot.llm.provider import LLMProvider, get_llm_client
from patch_pilot.config import Config
from patch_pilot.agents.state import (
    AgentSessionState,
    ExecutionStep,
)
from patch_pilot.agents.auditor import AuditorAgent
from patch_pilot.agents.test_synthesizer import TestSynthesizerAgent
from patch_pilot.agents.patch_generator import PatchGeneratorAgent
from patch_pilot.agents.reflector import ReflectorAgent


class SupervisorOrchestrator:
    """Master orchestrator executing the full review and self-healing workflow."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        max_repair_attempts: Optional[int] = None,
        sandbox_timeout: Optional[int] = None,
    ):
        self.llm = llm or get_llm_client()
        self.max_repair_attempts = max_repair_attempts or Config.MAX_REPAIR_ATTEMPTS
        self.sandbox = SandboxRunner(timeout_seconds=sandbox_timeout or Config.SANDBOX_TIMEOUT_SECONDS)
        
        # Sub-agents
        self.auditor = AuditorAgent(self.llm)
        self.synthesizer = TestSynthesizerAgent(self.llm)
        self.patch_gen = PatchGeneratorAgent(self.llm)
        self.reflector = ReflectorAgent(self.llm)

    def run_review(
        self,
        source_code: str,
        filepath: str = "target_file.py",
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> AgentSessionState:
        """
        Executes the complete multi-agent review and self-healing verification lifecycle.
        
        :param source_code: Raw Python code to review.
        :param filepath: Filename or relative path for context.
        :param progress_callback: Optional callback(stage: str, message: str) for live CLI updates.
        """
        def notify(stage: str, msg: str):
            if progress_callback:
                progress_callback(stage, msg)

        # 1. Structural AST Inspection
        notify("ast", "Performing static AST structural analysis...")
        inspection = CodeInspector.inspect_code(source_code, filepath=filepath)
        ast_summary = inspection.to_summary_prompt()

        # Initialize session state
        state = AgentSessionState(
            filepath=filepath,
            original_code=source_code,
            ast_summary=ast_summary,
        )

        # If syntax is invalid, audit focuses on syntax restoration
        if not inspection.syntax_valid:
            notify("ast_error", f"Syntax error detected: {inspection.syntax_error}")

        # 2. Security & Logic Audit
        notify("audit", "Auditor Agent: Scanning for logic bugs, CWEs, and edge cases...")
        audit_report = self.auditor.audit(source_code, ast_summary, filepath)
        state.audit_report = audit_report

        # 3. Test Synthesis
        notify("test_gen", "Test Synthesizer Agent: Generating reproduction test suite...")
        synthesized_test = self.synthesizer.synthesize(source_code, ast_summary, audit_report)
        state.synthesized_test = synthesized_test

        # 4. Initial Patch Synthesis
        notify("patch_gen", "Patch Generator Agent: Synthesizing defensive code fix...")
        current_patch = self.patch_gen.generate_patch(
            source_code, ast_summary, audit_report, synthesized_test
        )
        state.current_patch = current_patch

        # 5. Sandbox Verification & Self-Healing Loop
        for attempt in range(1, self.max_repair_attempts + 1):
            state.repair_attempts = attempt
            notify("sandbox", f"Sandbox: Verifying patch in isolated environment (Attempt {attempt}/{self.max_repair_attempts})...")

            result = self.sandbox.run_test(
                source_code=current_patch.patched_code,
                test_code=synthesized_test.test_code,
                module_name="target_module"
            )

            state.history.append(
                ExecutionStep(
                    attempt=attempt,
                    passed=result.passed,
                    duration_seconds=result.duration_seconds,
                    feedback=result.feedback_trace
                )
            )

            if result.passed:
                notify("verified", f"Verification SUCCEEDED on attempt {attempt}!")
                state.is_verified = True
                break
            else:
                notify("failed", f"Attempt {attempt} failed ({result.duration_seconds}s).")
                if attempt < self.max_repair_attempts:
                    notify("reflect", "Reflector Agent: Analyzing failure traceback to self-correct patch...")
                    current_patch = self.reflector.reflect_and_repair(
                        current_patch=current_patch,
                        synthesized_test=synthesized_test,
                        test_feedback=result.feedback_trace,
                        attempt=attempt
                    )
                    state.current_patch = current_patch

        notify("complete", "Review and verification pipeline completed.")
        return state
