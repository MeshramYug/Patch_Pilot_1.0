"""
Unit tests for the AST inspection engine.
"""

from patch_pilot.ast_engine.inspector import CodeInspector


SAMPLE_CODE = """
import math
from typing import List

class MathService:
    '''Service for math operations.'''
    def calculate(self, items: List[int]) -> int:
        total = 0
        for x in items:
            if x > 0:
                total += x
            else:
                total -= 1
        return total

def standalone_helper(flag: bool) -> str:
    if flag:
        return "yes"
    return "no"
"""


def test_ast_inspection_valid():
    report = CodeInspector.inspect_code(SAMPLE_CODE, filepath="test_sample.py")
    assert report.syntax_valid is True
    assert report.syntax_error is None
    assert len(report.classes) == 1
    assert report.classes[0].name == "MathService"
    assert "calculate" in report.classes[0].methods

    # Verify functions
    fn_names = [f.name for f in report.functions]
    assert "MathService.calculate" in fn_names
    assert "standalone_helper" in fn_names

    # Check complexity
    calc_fn = next(f for f in report.functions if f.name == "MathService.calculate")
    assert calc_fn.complexity >= 3  # for + if/else


def test_ast_inspection_syntax_error():
    broken_code = "def broken_func(:\n    pass"
    report = CodeInspector.inspect_code(broken_code, filepath="broken.py")
    assert report.syntax_valid is False
    assert report.syntax_error is not None
    assert "Line 1" in report.syntax_error


def test_ast_summary_prompt():
    report = CodeInspector.inspect_code(SAMPLE_CODE, filepath="sample.py")
    summary = report.to_summary_prompt()
    assert "Structural AST Analysis" in summary
    assert "MathService" in summary
    assert "calculate" in summary
