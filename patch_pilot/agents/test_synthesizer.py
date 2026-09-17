"""
Test Synthesizer Agent: Generates reproducible pytest suites targeted at discovered bugs.
"""

import json
from patch_pilot.agents.state import AuditReport, SynthesizedTest
from patch_pilot.llm.provider import LLMProvider


TEST_SYNTHESIZER_SYSTEM_PROMPT = """You are the Test Synthesizer Agent in the PatchPilot system.
Your mission is to generate a comprehensive, runnable `pytest` test suite that:
1. Re-creates the exact conditions where the identified bugs/flaws manifest.
2. Asserts correct defensive behavior and outputs.
3. Tests both the unhappy paths (edge cases, empty inputs, malformed types) and happy paths.

CRITICAL SANDBOX REQUIREMENT:
The module under test is named `target_module`.
Always import functions or classes like:
`from target_module import <function_or_class>`

You MUST respond strictly with a valid JSON object matching this schema:
{
  "test_code": "import pytest\\nfrom target_module import ...\\n\\ndef test_...():\\n    ...",
  "rationale": "Explanation of why these test cases validate the fix and prevent regressions."
}
"""


class TestSynthesizerAgent:
    """Specialized agent for generating automated pytest suites for code flaws."""
    __test__ = False

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def synthesize(
        self,
        source_code: str,
        ast_summary: str,
        audit_report: AuditReport
    ) -> SynthesizedTest:
        issues_str = "\n".join(
            f"- [{i.severity}] {i.title}: {i.description} (Line {i.line_number})"
            for i in audit_report.issues
        )

        user_prompt = (
            f"AUDIT FINDINGS:\n{issues_str}\n\n"
            f"AST METADATA:\n{ast_summary}\n\n"
            f"ORIGINAL CODE:\n```python\n{source_code}\n```\n\n"
            "Synthesize a robust pytest test suite targeting these issues. Respond in JSON."
        )

        response_text = self.llm.query(
            system_prompt=TEST_SYNTHESIZER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
            json_output=True
        )

        try:
            data = json.loads(response_text)
            return SynthesizedTest(**data)
        except Exception:
            return SynthesizedTest(
                test_code=(
                    "import pytest\n"
                    "import target_module\n\n"
                    "def test_module_loads():\n"
                    "    assert target_module is not None\n"
                ),
                rationale="Fallback smoke test generated due to unparsed output."
            )
