"""
Unit and integration tests for the multi-agent committee and supervisor orchestrator.
"""

from patch_pilot.llm.provider import LLMProvider
from patch_pilot.agents.auditor import AuditorAgent
from patch_pilot.agents.test_synthesizer import TestSynthesizerAgent
from patch_pilot.agents.patch_generator import PatchGeneratorAgent
from patch_pilot.agents.reflector import ReflectorAgent
from patch_pilot.agents.supervisor import SupervisorOrchestrator
from patch_pilot.reporter.markdown_builder import MarkdownReportBuilder


SAMPLE_BUGGY_CODE = """
def process_batch(items: list) -> dict:
    total = sum(items)
    return {'status': 'ok', 'average': total / len(items)}
"""


def test_auditor_agent():
    llm = LLMProvider(provider="mock")
    auditor = AuditorAgent(llm)
    report = auditor.audit(SAMPLE_BUGGY_CODE, "AST summary placeholder", "batch.py")
    assert report.summary != ""
    assert len(report.issues) > 0
    assert report.issues[0].severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def test_test_synthesizer_agent():
    llm = LLMProvider(provider="mock")
    auditor = AuditorAgent(llm)
    synthesizer = TestSynthesizerAgent(llm)

    audit_report = auditor.audit(SAMPLE_BUGGY_CODE, "AST summary", "batch.py")
    test_suite = synthesizer.synthesize(SAMPLE_BUGGY_CODE, "AST summary", audit_report)

    assert "import pytest" in test_suite.test_code
    assert "target_module" in test_suite.test_code


def test_supervisor_end_to_end():
    llm = LLMProvider(provider="mock")
    supervisor = SupervisorOrchestrator(llm=llm, max_repair_attempts=2)

    session = supervisor.run_review(
        source_code=SAMPLE_BUGGY_CODE,
        filepath="batch.py"
    )

    assert session.audit_report is not None
    assert session.synthesized_test is not None
    assert session.current_patch is not None
    assert session.is_verified is True
    assert len(session.history) > 0


def test_markdown_report_builder():
    llm = LLMProvider(provider="mock")
    supervisor = SupervisorOrchestrator(llm=llm, max_repair_attempts=1)
    session = supervisor.run_review(source_code=SAMPLE_BUGGY_CODE, filepath="batch.py")

    report_md = MarkdownReportBuilder.build_pr_comment(session)
    assert "PatchPilot Automated Code Review" in report_md
    assert "VERIFIED" in report_md
    assert "Audit Findings" in report_md
    assert "Unified Diff" in report_md
