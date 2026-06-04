from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import chat, databases, datasets
from backend.schemas import HealthResponse


app = FastAPI(
    title="CSV Data Analysis Agent API",
    description="FastAPI backend for CSV EDA, business analysis, and LangChain Agent chat.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(chat.router)
app.include_router(databases.router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="csv-data-analysis-agent")
