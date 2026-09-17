"""
Python AST Inspector.
Extracts semantic code structure, function bounds, arguments, and cyclomatic complexity.
"""

import ast
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class FunctionMetadata:
    """Metadata for an individual Python function or method."""
    name: str
    start_line: int
    end_line: int
    args: List[str]
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    complexity: int = 1
    source_slice: str = ""
    is_async: bool = False


@dataclass
class ClassMetadata:
    """Metadata for a Python class definition."""
    name: str
    start_line: int
    end_line: int
    bases: List[str]
    methods: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class InspectionReport:
    """Full AST inspection report for a source file."""
    filepath: str
    syntax_valid: bool = True
    syntax_error: Optional[str] = None
    total_lines: int = 0
    imports: List[str] = field(default_factory=list)
    functions: List[FunctionMetadata] = field(default_factory=list)
    classes: List[ClassMetadata] = field(default_factory=list)
    average_complexity: float = 1.0

    def to_summary_prompt(self) -> str:
        """Generates a concise markdown summary for agent context."""
        if not self.syntax_valid:
            return f"❌ Syntax Error in {self.filepath}: {self.syntax_error}"
        
        lines = [
            f"### Structural AST Analysis: `{self.filepath}`",
            f"- **Total Lines**: {self.total_lines}",
            f"- **Imports**: {', '.join(self.imports) if self.imports else 'None'}",
            f"- **Classes ({len(self.classes)})**: {', '.join(c.name for c in self.classes) if self.classes else 'None'}",
            f"- **Functions ({len(self.functions)})**:",
        ]
        for fn in self.functions:
            ret = f" -> {fn.return_type}" if fn.return_type else ""
            lines.append(
                f"  - `{fn.name}({', '.join(fn.args)}){ret}` "
                f"[Lines {fn.start_line}-{fn.end_line}] (Complexity: {fn.complexity})"
            )
        return "\n".join(lines)


class ComplexityVisitor(ast.NodeVisitor):
    """Calculates McCabe cyclomatic complexity for a function AST node."""
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self, node):
        self.complexity += len(node.handlers)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        self.complexity += 1
        self.generic_visit(node)


class CodeInspector:
    """Performs static AST inspection on Python source code."""

    @staticmethod
    def inspect_code(source_code: str, filepath: str = "<anonymous>") -> InspectionReport:
        lines = source_code.splitlines()
        report = InspectionReport(filepath=filepath, total_lines=len(lines))

        try:
            tree = ast.parse(source_code, filename=filepath)
        except SyntaxError as e:
            report.syntax_valid = False
            report.syntax_error = f"Line {e.lineno}, Col {e.offset}: {e.msg}"
            return report

        # Collect Imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    report.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    report.imports.append(f"{mod}.{alias.name}")

        # Top-level and class-level functions & classes
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_meta = CodeInspector._parse_function(node, lines)
                report.functions.append(fn_meta)

            elif isinstance(node, ast.ClassDef):
                cls_meta = CodeInspector._parse_class(node, lines)
                report.classes.append(cls_meta)
                # Parse class methods
                for sub_node in node.body:
                    if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_meta = CodeInspector._parse_function(sub_node, lines, prefix=f"{node.name}.")
                        report.functions.append(method_meta)

        if report.functions:
            total_comp = sum(f.complexity for f in report.functions)
            report.average_complexity = round(total_comp / len(report.functions), 2)

        return report

    @staticmethod
    def _parse_function(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: List[str],
        prefix: str = ""
    ) -> FunctionMetadata:
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)

        # Arguments
        args = []
        for a in node.args.args:
            arg_str = a.arg
            if a.annotation:
                arg_str += f": {ast.unparse(a.annotation)}"
            args.append(arg_str)

        # Return annotation
        ret_type = ast.unparse(node.returns) if node.returns else None

        # Docstring
        docstring = ast.get_docstring(node)

        # Complexity
        vis = ComplexityVisitor()
        vis.visit(node)

        # Source slice
        source_slice = "\n".join(lines[start_line - 1 : end_line])

        return FunctionMetadata(
            name=f"{prefix}{node.name}",
            start_line=start_line,
            end_line=end_line,
            args=args,
            return_type=ret_type,
            docstring=docstring,
            complexity=vis.complexity,
            source_slice=source_slice,
            is_async=isinstance(node, ast.AsyncFunctionDef)
        )

    @staticmethod
    def _parse_class(node: ast.ClassDef, lines: List[str]) -> ClassMetadata:
        bases = [ast.unparse(b) for b in node.bases]
        methods = [
            m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        return ClassMetadata(
            name=node.name,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            bases=bases,
            methods=methods,
            docstring=ast.get_docstring(node)
        )
