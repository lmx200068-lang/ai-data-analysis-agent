from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class LocalDatasetRequest(BaseModel):
    path: str = Field(..., description="Local CSV file path.")


class DatasetSummary(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    preview: list[dict[str, Any]]


class DatasetSchemaResponse(BaseModel):
    dataset_id: str
    schema_summary: dict[str, Any]


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummary]


class ChatRequest(BaseModel):
    dataset_id: str
    question: str


class ToolCallRecord(BaseModel):
    name: str
    args: dict[str, Any]
    result: dict[str, Any]


class ChartSpec(BaseModel):
    type: Literal["metric", "bar", "line", "table"]
    title: str
    data: Any
    x: str | None = None
    y: str | None = None


class ChatResponse(BaseModel):
    dataset_id: str
    answer: str
    tool_calls: list[ToolCallRecord]
    charts: list[ChartSpec]


class SQLiteConnectRequest(BaseModel):
    path: str = Field(..., description="Local SQLite .db/.sqlite file path.")


class DatabaseSummary(BaseModel):
    database_id: str
    filename: str
    tables: list[str]


class DatabaseListResponse(BaseModel):
    databases: list[DatabaseSummary]


class TableSchemaResponse(BaseModel):
    database_id: str
    table_name: str
    table_schema: dict[str, Any]


class TablePreviewResponse(BaseModel):
    database_id: str
    table_name: str
    preview: dict[str, Any]


class SQLQueryRequest(BaseModel):
    database_id: str
    sql: str
    limit: int = 100


class SQLQueryResponse(BaseModel):
    database_id: str
    result: dict[str, Any]


class DatabaseChatRequest(BaseModel):
    database_id: str
    question: str


class DatabaseChatResponse(BaseModel):
    database_id: str
    answer: str
    tool_calls: list[ToolCallRecord]
    charts: list[ChartSpec]
