from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sql_agent import SQLiteAgent
from sql_tools import SQLiteDataTools


@dataclass
class DatabaseSession:
    database_id: str
    db_path: Path
    sql_tools: SQLiteDataTools
    agent: SQLiteAgent


class DatabaseStore:
    def __init__(self) -> None:
        self._sessions: dict[str, DatabaseSession] = {}

    def list_databases(self) -> list[DatabaseSession]:
        return list(self._sessions.values())

    def get(self, database_id: str) -> DatabaseSession | None:
        return self._sessions.get(database_id)

    def connect_sqlite(self, db_path: Path) -> DatabaseSession:
        if not db_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {db_path}")

        sql_tools = SQLiteDataTools(db_path)
        session = DatabaseSession(
            database_id=str(uuid4()),
            db_path=db_path,
            sql_tools=sql_tools,
            agent=SQLiteAgent(sql_tools),
        )
        self._sessions[session.database_id] = session
        return session

    @staticmethod
    def to_summary(session: DatabaseSession) -> dict:
        return {
            "database_id": session.database_id,
            "filename": session.db_path.name,
            "tables": session.sql_tools.list_tables()["tables"],
        }


database_store = DatabaseStore()

