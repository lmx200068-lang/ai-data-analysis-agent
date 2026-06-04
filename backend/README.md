# FastAPI Backend

This backend exposes the CSV data analysis Agent as HTTP APIs.

## Run

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## Main Endpoints

- `GET /health`
- `GET /datasets`
- `POST /datasets/upload`
- `POST /datasets/load-local`
- `GET /datasets/{dataset_id}/schema`
- `POST /chat`
- `GET /databases`
- `POST /databases/connect-sqlite`
- `GET /databases/{database_id}/tables`
- `GET /databases/{database_id}/tables/{table_name}/schema`
- `GET /databases/{database_id}/tables/{table_name}/preview`
- `POST /databases/{database_id}/query`
- `POST /databases/{database_id}/chat`

## Typical Flow

1. Load a CSV:

```json
POST /datasets/load-local
{
  "path": "SuperMarket Analysis.csv"
}
```

2. Copy the returned `dataset_id`.

3. Ask a question:

```json
POST /chat
{
  "dataset_id": "your-dataset-id",
  "question": "这个超市的核心业务指标怎么样？"
}
```

The chat response includes:

- `answer`: natural-language analysis
- `tool_calls`: tools used by the Agent
- `charts`: structured chart specs for frontend rendering

## SQLite Flow

Create the demo SQLite database from the supermarket CSV:

```powershell
python scripts/create_demo_sqlite.py
```

Connect the SQLite database:

```json
POST /databases/connect-sqlite
{
  "path": "supermarket_demo.db"
}
```

Run a read-only SQL query:

```json
POST /databases/{database_id}/query
{
  "database_id": "your-database-id",
  "sql": "SELECT City, SUM(Sales) AS total_sales FROM supermarket_sales GROUP BY City ORDER BY total_sales DESC",
  "limit": 10
}
```

Ask the database Agent:

```json
POST /databases/{database_id}/chat
{
  "database_id": "your-database-id",
  "question": "哪个城市销售额最高？"
}
```

SQLite queries are read-only. Mutating statements such as `DROP`, `DELETE`, `UPDATE`, and `INSERT` are blocked.
