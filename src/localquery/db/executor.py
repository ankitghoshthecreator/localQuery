import sqlite3
from localquery.db.schema import DB_PATH

class DBExecutor:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def execute_query(self, sql: str) -> dict:
        """
        Executes a SQL query safely and returns the results.
        Returns a dictionary with 'columns', 'rows', and 'error' (if any).
        """
        # Security: In a real system, you'd ensure the connection is read-only.
        # SQLite read-only URI: file:finance.db?mode=ro
        try:
            # Check for modifying queries minimally
            sql_upper = sql.upper().strip()
            if any(sql_upper.startswith(kw) for kw in ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE']):
                return {"columns": [], "rows": [], "error": "Only SELECT queries are allowed."}

            # execute
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute(sql)
            
            columns = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            conn.close()
            return {"columns": columns, "rows": rows, "error": None}
            
        except sqlite3.Error as e:
            return {"columns": [], "rows": [], "error": str(e)}
        except Exception as e:
            return {"columns": [], "rows": [], "error": str(e)}

    def format_results(self, result: dict) -> str:
        """Formats the result dictionary into a readable markdown table."""
        if result['error']:
            return f"Error executing query: {result['error']}"
        
        if not result['rows']:
            return "No results found."
            
        columns = result['columns']
        rows = result['rows']
        
        # Calculate column widths
        col_widths = [len(str(col)) for col in columns]
        for row in rows:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(val)))
                
        # Format table
        header = "| " + " | ".join(str(col).ljust(width) for col, width in zip(columns, col_widths)) + " |"
        separator = "|" + "|".join("-" * (width + 2) for width in col_widths) + "|"
        
        table = [header, separator]
        for row in rows:
            row_str = "| " + " | ".join(str(val).ljust(width) for val, width in zip(row, col_widths)) + " |"
            table.append(row_str)
            
        return "\n".join(table)
