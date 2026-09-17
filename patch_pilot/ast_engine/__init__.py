"""
AST Engine for structural code inspection and static metadata extraction.
"""

from patch_pilot.ast_engine.inspector import (
    CodeInspector,
    FunctionMetadata,
    ClassMetadata,
    InspectionReport,
)

__all__ = [
    "CodeInspector",
    "FunctionMetadata",
    "ClassMetadata",
    "InspectionReport",
]
