import re
import sqlite3
from pathlib import Path
from typing import Any


BLOCKED_SQL_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "vacuum",
}


class SQLiteDataTools:
    def __init__(self, db_path: Path):
        if not db_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {db_path}")

        self.db_path = db_path

    def list_tables(self) -> dict[str, Any]:
        query = """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """
        rows = self._fetch_all(query)
        return {"tables": [row["name"] for row in rows]}

    def get_table_schema(self, table_name: str) -> dict[str, Any]:
        if not self._table_exists(table_name):
            return {"error": f"Table not found: {table_name}", "tables": self.list_tables()["tables"]}

        with self._connect() as conn:
            columns = conn.execute(f"PRAGMA table_info({self._quote_identifier(table_name)})").fetchall()

        return {
            "table_name": table_name,
            "columns": [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default_value": row["dflt_value"],
                    "primary_key": bool(row["pk"]),
                }
                for row in columns
            ],
        }

    def preview_table(self, table_name: str, limit: int = 10) -> dict[str, Any]:
        limit = self._normalize_limit(limit)

        if not self._table_exists(table_name):
            return {"error": f"Table not found: {table_name}", "tables": self.list_tables()["tables"]}

        sql = f"SELECT * FROM {self._quote_identifier(table_name)} LIMIT {limit}"
        return {
            "table_name": table_name,
            "limit": limit,
            "rows": self._fetch_all(sql),
        }

    def run_readonly_query(self, sql: str, limit: int = 100) -> dict[str, Any]:
        limit = self._normalize_limit(limit)
        cleaned_sql = self._validate_readonly_sql(sql)
        limited_sql = self._ensure_limit(cleaned_sql, limit)
        rows = self._fetch_all(limited_sql)

        return {
            "sql": limited_sql,
            "limit": limit,
            "row_count": len(rows),
            "rows": rows,
        }

    def table_summary(self, table_name: str) -> dict[str, Any]:
        if not self._table_exists(table_name):
            return {"error": f"Table not found: {table_name}", "tables": self.list_tables()["tables"]}

        quoted = self._quote_identifier(table_name)

        with self._connect() as conn:
            row_count = conn.execute(f"SELECT COUNT(*) AS count FROM {quoted}").fetchone()["count"]

        schema = self.get_table_schema(table_name)
        preview = self.preview_table(table_name, limit=5).get("rows", [])

        return {
            "table_name": table_name,
            "row_count": int(row_count),
            "schema": schema["columns"],
            "preview": preview,
        }

    def database_summary(self) -> dict[str, Any]:
        tables = self.list_tables()["tables"]
        return {
            "database": self.db_path.name,
            "tables": [self.table_summary(table) for table in tables],
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def _fetch_all(self, sql: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [self._json_safe_row(row) for row in rows]

    def _table_exists(self, table_name: str) -> bool:
        query = """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            LIMIT 1
        """
        with self._connect() as conn:
            row = conn.execute(query, (table_name,)).fetchone()
        return row is not None

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    @classmethod
    def _json_safe_row(cls, row: sqlite3.Row) -> dict[str, Any]:
        return {key: cls._json_safe_value(row[key]) for key in row.keys()}

    @staticmethod
    def _json_safe_value(value: Any) -> Any:
        if isinstance(value, bytes):
            return f"<BLOB {len(value)} bytes>"

        if isinstance(value, bytearray):
            return f"<BLOB {len(value)} bytes>"

        if isinstance(value, memoryview):
            return f"<BLOB {value.nbytes} bytes>"

        return value

    @staticmethod
    def _normalize_limit(limit: int) -> int:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 100
        return max(1, min(limit, 500))

    @staticmethod
    def _validate_readonly_sql(sql: str) -> str:
        cleaned_sql = sql.strip().rstrip(";")
        lowered = cleaned_sql.lower()

        if not lowered.startswith(("select", "with")):
            raise ValueError("Only SELECT or WITH queries are allowed.")

        statements = [part for part in cleaned_sql.split(";") if part.strip()]
        if len(statements) > 1:
            raise ValueError("Only one SQL statement is allowed.")

        tokens = set(re.findall(r"[a-zA-Z_]+", lowered))
        blocked = sorted(tokens & BLOCKED_SQL_KEYWORDS)
        if blocked:
            raise ValueError(f"Blocked SQL keyword(s): {', '.join(blocked)}")

        return cleaned_sql

    @staticmethod
    def _ensure_limit(sql: str, limit: int) -> str:
        if re.search(r"\blimit\s+\d+\b", sql, flags=re.IGNORECASE):
            return sql
        return f"{sql} LIMIT {limit}"
