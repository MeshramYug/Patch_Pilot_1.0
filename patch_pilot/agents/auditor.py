"""
Auditor Agent: Scans source code and AST metadata for logic flaws, security issues, and edge cases.
"""

import json
from patch_pilot.agents.state import AuditReport, IssueFinding
from patch_pilot.llm.provider import LLMProvider


AUDITOR_SYSTEM_PROMPT = """You are the Lead Security & Code Quality Auditor Agent in the PatchPilot system.
Your mission is to perform deep static review of the provided Python source code.
Focus on:
1. Critical Logic Bugs: Off-by-one errors, unhandled NoneType dereferences, zero-division, incorrect operator precedence.
2. Security Vulnerabilities: SQL injection, path traversal, unsafe deserialization, exposed credentials, CWE flaws.
3. Concurrency / State Hazards: Race conditions, shared mutable defaults, unclosed resource handles.
4. Edge Case Omissions: Empty collections, negative numbers, missing type validations.

You MUST respond strictly with a valid JSON object matching this schema:
{
  "summary": "High-level summary of your audit findings.",
  "issues": [
    {
      "title": "Short descriptive title of the issue",
      "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
      "line_number": 12,
      "description": "Detailed explanation of why this code fails or is vulnerable.",
      "cwe_id": "CWE-369" (or null if not a security flaw),
      "suggested_fix": "Concrete instructions on how to patch the flaw."
    }
  ]
}
"""


class AuditorAgent:
    """Specialized agent for discovering code flaws and security vulnerabilities."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def audit(self, source_code: str, ast_summary: str, filepath: str) -> AuditReport:
        user_prompt = (
            f"FILEPATH: {filepath}\n\n"
            f"AST CONTEXT:\n{ast_summary}\n\n"
            f"SOURCE CODE:\n```python\n{source_code}\n```\n\n"
            "Analyze the code and produce your structured audit report in JSON."
        )

        response_text = self.llm.query(
            system_prompt=AUDITOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            json_output=True
        )

        try:
            data = json.loads(response_text)
            return AuditReport(**data)
        except Exception:
            # Fallback if raw text returned
            return AuditReport(
                summary="Audit completed with unstructured findings.",
                issues=[
                    IssueFinding(
                        title="Potential Logic / Security Flaw",
                        severity="MEDIUM",
                        description=response_text[:300],
                        suggested_fix="Review function bounds and input assertions."
                    )
                ]
            )
