"""
Patch Generator Agent: Generates defensive code patches to resolve issues and satisfy tests.
"""

import json
from patch_pilot.agents.state import AuditReport, SynthesizedTest, PatchProposal
from patch_pilot.llm.provider import LLMProvider


PATCH_GENERATOR_SYSTEM_PROMPT = """You are the Patch Generator Agent in the PatchPilot system.
Your mission is to produce a clean, minimal, robust patch for the provided Python code that:
1. Resolves all flaws identified by the Auditor Agent.
2. Ensures all synthesized pytest cases will PASS.
3. Preserves existing function signatures, comments, and non-defective behavior.
4. Adheres to Python best practices (type hints, PEP 8, guard clauses).

You MUST respond strictly with a valid JSON object matching this schema:
{
  "patch_explanation": "Concise summary of the architectural or logic changes made.",
  "patched_code": "Full updated Python code for the file, complete and ready to run."
}
"""


class PatchGeneratorAgent:
    """Specialized agent for synthesizing bug fixes and defensive patches."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def generate_patch(
        self,
        source_code: str,
        ast_summary: str,
        audit_report: AuditReport,
        synthesized_test: SynthesizedTest
    ) -> PatchProposal:
        issues_str = "\n".join(
            f"- [{i.severity}] {i.title}: {i.suggested_fix}"
            for i in audit_report.issues
        )

        user_prompt = (
            f"AUDIT ISSUES TO RESOLVE:\n{issues_str}\n\n"
            f"TEST SUITE TO SATISFY:\n```python\n{synthesized_test.test_code}\n```\n\n"
            f"AST METADATA:\n{ast_summary}\n\n"
            f"ORIGINAL CODE:\n```python\n{source_code}\n```\n\n"
            "Generate the patched version of the code that resolves all issues and passes the tests."
        )

        response_text = self.llm.query(
            system_prompt=PATCH_GENERATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            json_output=True
        )

        try:
            data = json.loads(response_text)
            return PatchProposal(**data)
        except Exception:
            return PatchProposal(
                patch_explanation="Fallback patch preserving original code.",
                patched_code=source_code
            )
