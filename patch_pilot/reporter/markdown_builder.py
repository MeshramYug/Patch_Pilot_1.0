"""
Markdown Report Builder for GitHub PR Comments and Automated Reviews.
"""

import difflib
from patch_pilot.agents.state import AgentSessionState


class MarkdownReportBuilder:
    """Generates structured GitHub PR review comments in markdown."""

    @staticmethod
    def build_pr_comment(state: AgentSessionState) -> str:
        """Constructs a complete, formatted GitHub PR review comment."""
        status_badge = "🟢 **VERIFIED (TESTS PASSING)**" if state.is_verified else "🔴 **UNVERIFIED (REQUIRES MANUAL REVIEW)**"
        
        lines = [
            f"## 🤖 PatchPilot Automated Code Review & Patch",
            f"**File**: `{state.filepath}` | **Status**: {status_badge}",
            f"**Self-Healing Attempts**: `{state.repair_attempts}` | **Provider**: `{state.history[-1].passed if state.history else 'N/A'}`",
            "",
            "---",
            "### 🔍 Audit Findings Summary",
        ]

        if state.audit_report:
            lines.append(f"> {state.audit_report.summary}\n")
            lines.append("| Severity | Issue | Line | CWE | Suggested Fix |")
            lines.append("| :--- | :--- | :---: | :---: | :--- |")
            for issue in state.audit_report.issues:
                cwe = f"`{issue.cwe_id}`" if issue.cwe_id else "N/A"
                line = str(issue.line_number) if issue.line_number else "-"
                lines.append(f"| **{issue.severity}** | {issue.title} | {line} | {cwe} | {issue.suggested_fix} |")
        else:
            lines.append("*No issues identified.*")

        lines.append("\n---")
        lines.append("### 🧪 Synthesized Regression Tests")
        if state.synthesized_test:
            lines.append(f"*{state.synthesized_test.rationale}*")
            lines.append("<details><summary>Click to view pytest suite</summary>\n")
            lines.append("```python")
            lines.append(state.synthesized_test.test_code)
            lines.append("```\n</details>")
        else:
            lines.append("*No tests synthesized.*")

        lines.append("\n---")
        lines.append("### 🛠️ Proposed Patch & Unified Diff")
        if state.current_patch:
            lines.append(f"**Explanation**: {state.current_patch.patch_explanation}\n")
            
            # Generate unified diff
            diff = difflib.unified_diff(
                state.original_code.splitlines(),
                state.current_patch.patched_code.splitlines(),
                fromfile=f"a/{state.filepath}",
                tofile=f"b/{state.filepath}",
                lineterm=""
            )
            diff_text = "\n".join(diff)

            if diff_text.strip():
                lines.append("```diff")
                lines.append(diff_text)
                lines.append("```")
            else:
                lines.append("*No code changes required.*")

            lines.append("\n<details><summary>Click to view full patched file</summary>\n")
            lines.append("```python")
            lines.append(state.current_patch.patched_code)
            lines.append("```\n</details>")

        lines.append("\n---")
        lines.append("<sub>Generated autonomously by [PatchPilot](https://github.com/yugme/patch-pilot) • Multi-Agent Code Intelligence</sub>")

        return "\n".join(lines)
