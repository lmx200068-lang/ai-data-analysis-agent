from fastapi import APIRouter, HTTPException

from backend.schemas import ChatRequest, ChatResponse, ChartSpec, ToolCallRecord
from backend.services.agent_service import ask_agent, build_chart_specs
from backend.services.dataset_store import dataset_store


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session = dataset_store.get(request.dataset_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        answer, tool_calls, _tool_log = ask_agent(session, request.question)
        charts = build_chart_specs(tool_calls)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        dataset_id=request.dataset_id,
        answer=answer,
        tool_calls=[ToolCallRecord(**tool_call) for tool_call in tool_calls],
        charts=[ChartSpec(**chart) for chart in charts],
    )

