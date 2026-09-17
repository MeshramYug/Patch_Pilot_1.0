"""
Sample buggy module: Authentication Service.
Contains critical security vulnerabilities (CWE-89: SQL Injection, CWE-306: Missing Authentication).
"""

import sqlite3
from typing import Optional, Dict, Any


def authenticate_user(db_conn: sqlite3.Connection, username: str, password_hash: str) -> Optional[Dict[str, Any]]:
    """
    Validates user credentials against database.
    VULNERABILITY: Raw SQL string formatting allows SQL Injection (CWE-89).
    """
    cursor = db_conn.cursor()
    # Critical Security Vulnerability: SQL Injection via f-string
    query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password_hash}'"
    cursor.execute(query)
    row = cursor.fetchone()
    
    if row:
        return {"id": row[0], "username": row[1], "role": row[2]}
    return None


def verify_session_token(token: Optional[str]) -> bool:
    """
    Validates session token length and prefix.
    BUG: Fails with AttributeError if token is None.
    """
    # Bug: Unhandled NoneType
    return token.startswith("tok_") and len(token) >= 32
