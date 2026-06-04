from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.schemas import (
    DatabaseChatRequest,
    DatabaseChatResponse,
    DatabaseListResponse,
    DatabaseSummary,
    SQLiteConnectRequest,
    SQLQueryRequest,
    SQLQueryResponse,
    TablePreviewResponse,
    TableSchemaResponse,
    ToolCallRecord,
)
from backend.services.database_store import database_store
from backend.services.agent_service import build_chart_specs
from config import BASE_DIR


router = APIRouter(prefix="/databases", tags=["databases"])


@router.get("", response_model=DatabaseListResponse)
def list_databases() -> DatabaseListResponse:
    return DatabaseListResponse(
        databases=[
            DatabaseSummary(**database_store.to_summary(session))
            for session in database_store.list_databases()
        ]
    )


@router.post("/connect-sqlite", response_model=DatabaseSummary)
def connect_sqlite(request: SQLiteConnectRequest) -> DatabaseSummary:
    db_path = Path(request.path.strip().strip('"').strip("'"))

    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    try:
        session = database_store.connect_sqlite(db_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DatabaseSummary(**database_store.to_summary(session))


@router.get("/{database_id}/tables")
def list_tables(database_id: str) -> dict:
    session = database_store.get(database_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Database not found.")

    return session.sql_tools.list_tables()


@router.get("/{database_id}/tables/{table_name}/schema", response_model=TableSchemaResponse)
def get_table_schema(database_id: str, table_name: str) -> TableSchemaResponse:
    session = database_store.get(database_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Database not found.")

    return TableSchemaResponse(
        database_id=database_id,
        table_name=table_name,
        table_schema=session.sql_tools.get_table_schema(table_name),
    )


@router.get("/{database_id}/tables/{table_name}/preview", response_model=TablePreviewResponse)
def preview_table(database_id: str, table_name: str, limit: int = 10) -> TablePreviewResponse:
    session = database_store.get(database_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Database not found.")

    return TablePreviewResponse(
        database_id=database_id,
        table_name=table_name,
        preview=session.sql_tools.preview_table(table_name, limit=limit),
    )


@router.post("/{database_id}/query", response_model=SQLQueryResponse)
def run_query(database_id: str, request: SQLQueryRequest) -> SQLQueryResponse:
    if database_id != request.database_id:
        raise HTTPException(status_code=400, detail="database_id mismatch.")

    session = database_store.get(database_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Database not found.")

    try:
        result = session.sql_tools.run_readonly_query(request.sql, limit=request.limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SQLQueryResponse(database_id=database_id, result=result)


@router.post("/{database_id}/chat", response_model=DatabaseChatResponse)
def chat_with_database(database_id: str, request: DatabaseChatRequest) -> DatabaseChatResponse:
    if database_id != request.database_id:
        raise HTTPException(status_code=400, detail="database_id mismatch.")

    session = database_store.get(database_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Database not found.")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        answer = session.agent.ask(request.question)
        tool_calls = list(getattr(session.agent, "last_tool_calls", []))
        charts = build_chart_specs(tool_calls)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DatabaseChatResponse(
        database_id=database_id,
        answer=answer,
        tool_calls=[ToolCallRecord(**tool_call) for tool_call in tool_calls],
        charts=[chart for chart in charts],
    )
