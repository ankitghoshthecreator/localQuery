"""
LocalQuery DB Executor
========================
Safely executes read-only SQL queries against a local SQLite database
and formats results as Markdown tables.
"""

from __future__ import annotations

import sqlite3
from typing import Dict, Any, List


class DBExecutor:
    """
    Executes SELECT queries against a local SQLite database.

    Only SELECT statements are permitted — any attempt to run DDL or DML
    (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE) is rejected immediately
    without touching the database.

    Args:
        db_path: Path to the SQLite database file.
    """

    # Keywords that indicate a write/destructive operation
    _DISALLOWED_PREFIXES = frozenset(
        {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "TRUNCATE"}
    )

    def __init__(self, db_path: str):
        self.db_path = db_path

    def execute_query(self, sql: str) -> Dict[str, Any]:
        """
        Execute a SQL query safely and return the results.

        Args:
            sql: The SQL string to execute.

        Returns:
            A dict with:
              - columns : list of column name strings
              - rows    : list of tuples (one per result row)
              - error   : error message string, or None on success
        """
        sql_stripped = sql.strip()
        first_keyword = sql_stripped.upper().split()[0] if sql_stripped else ""

        if first_keyword in self._DISALLOWED_PREFIXES:
            return {
                "columns": [],
                "rows": [],
                "error": "Only SELECT queries are allowed.",
            }

        try:
            # Open in read-only mode via the URI interface
            uri = f"file:{self.db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            cursor = conn.cursor()
            cursor.execute(sql_stripped)

            columns: List[str] = (
                [desc[0] for desc in cursor.description]
                if cursor.description
                else []
            )
            rows = cursor.fetchall()
            conn.close()

            return {"columns": columns, "rows": rows, "error": None}

        except sqlite3.Error as exc:
            return {"columns": [], "rows": [], "error": str(exc)}
        except Exception as exc:
            return {"columns": [], "rows": [], "error": str(exc)}

    def format_results(self, result: Dict[str, Any]) -> str:
        """
        Format a query result dict into a Markdown table string.

        Args:
            result: Dict as returned by :meth:`execute_query`.

        Returns:
            A multi-line Markdown table string, or an error/no-data message.
        """
        if result["error"]:
            return f"Error executing query: {result['error']}"

        columns = result["columns"]
        rows = result["rows"]

        if not rows:
            return "No results found."

        # Calculate column widths (minimum = column name length)
        col_widths = [len(col) for col in columns]
        for row in rows:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(val)))

        def _row_str(values: list) -> str:
            return (
                "| "
                + " | ".join(
                    str(v).ljust(w) for v, w in zip(values, col_widths)
                )
                + " |"
            )

        separator = "|" + "|".join("-" * (w + 2) for w in col_widths) + "|"

        lines = [_row_str(columns), separator]
        lines.extend(_row_str(list(row)) for row in rows)
        return "\n".join(lines)

    def get_row_count(self, table: str) -> int:
        """Return the number of rows in *table*, or -1 on error."""
        res = self.execute_query(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
        if res["error"] or not res["rows"]:
            return -1
        return res["rows"][0][0]
