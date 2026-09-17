"""
Sample buggy module: Data Processor Service.
Contains intentional edge-case logic bugs (ZeroDivisionError, missing None validation).
"""

from typing import List, Dict, Any, Optional


def calculate_metrics(values: List[float]) -> Dict[str, float]:
    """
    Computes statistical metrics over a numeric collection.
    BUG: Fails with ZeroDivisionError when passed an empty list.
    """
    total = sum(values)
    # Bug: If values is empty, len(values) is 0 -> ZeroDivisionError
    average = total / len(values)
    
    # Bug: Off-by-one / IndexError if values has fewer than 2 elements
    range_spread = values[-1] - values[0]

    return {
        "count": float(len(values)),
        "total": float(total),
        "average": float(average),
        "spread": float(range_spread)
    }


def process_user_records(records: Optional[List[Dict[str, Any]]]) -> List[str]:
    """
    Extracts uppercase names from user records.
    BUG: Does not validate that `records` is not None, nor that record['name'] is not None.
    """
    # Bug: Will raise TypeError if records is None
    names = []
    for r in records:
        # Bug: KeyError or AttributeError if 'name' is missing or None
        names.append(r["name"].upper())
    return names
