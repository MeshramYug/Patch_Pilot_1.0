"""
Reflector Agent: Analyzes sandbox test failure feedback to iteratively fix code patches.
"""

import json
from patch_pilot.agents.state import PatchProposal, SynthesizedTest
from patch_pilot.llm.provider import LLMProvider


REFLECTOR_SYSTEM_PROMPT = """You are the Reflector & Self-Healing Agent in the PatchPilot system.
Your mission is to examine a failed test execution traceback and correct the proposed patch.

You will be given:
1. The currently proposed code patch.
2. The pytest test suite that was executed.
3. The exact stdout / stderr / traceback from the failure.

Analyze the exact reason for the failure (e.g. AssertionError, KeyError, TypeError, unexpected return value)
and generate a corrected version of the code that will pass the test.

You MUST respond strictly with a valid JSON object matching this schema:
{
  "patch_explanation": "Detailed explanation of why the previous attempt failed and what was adjusted.",
  "patched_code": "The complete, revised Python code ready for re-testing."
}
"""


class ReflectorAgent:
    """Specialized agent for analyzing test failures and self-correcting patches."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def reflect_and_repair(
        self,
        current_patch: PatchProposal,
        synthesized_test: SynthesizedTest,
        test_feedback: str,
        attempt: int
    ) -> PatchProposal:
        user_prompt = (
            f"ATTEMPT NUMBER: {attempt}\n\n"
            f"TEST FEEDBACK / TRACEBACK:\n```text\n{test_feedback}\n```\n\n"
            f"CURRENT PATCHED CODE:\n```python\n{current_patch.patched_code}\n```\n\n"
            f"TEST SUITE:\n```python\n{synthesized_test.test_code}\n```\n\n"
            "Analyze the failure traceback and produce a revised patch that resolves the failure."
        )

        response_text = self.llm.query(
            system_prompt=REFLECTOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            json_output=True
        )

        try:
            data = json.loads(response_text)
            return PatchProposal(**data)
        except Exception:
            return current_patch
