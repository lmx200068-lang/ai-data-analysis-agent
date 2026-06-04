from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas import DatasetListResponse, DatasetSchemaResponse, DatasetSummary, LocalDatasetRequest
from backend.services.dataset_store import dataset_store
from config import BASE_DIR


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=DatasetListResponse)
def list_datasets() -> DatasetListResponse:
    return DatasetListResponse(
        datasets=[DatasetSummary(**dataset_store.to_summary(session)) for session in dataset_store.list_datasets()]
    )


@router.post("/upload", response_model=DatasetSummary)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetSummary:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    try:
        session = dataset_store.save_upload(file.filename, content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DatasetSummary(**dataset_store.to_summary(session))


@router.post("/load-local", response_model=DatasetSummary)
def load_local_dataset(request: LocalDatasetRequest) -> DatasetSummary:
    csv_path = Path(request.path.strip().strip('"').strip("'"))

    if not csv_path.is_absolute():
        csv_path = BASE_DIR / csv_path

    try:
        session = dataset_store.create_from_path(csv_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DatasetSummary(**dataset_store.to_summary(session))


@router.get("/{dataset_id}/schema", response_model=DatasetSchemaResponse)
def get_dataset_schema(dataset_id: str) -> DatasetSchemaResponse:
    session = dataset_store.get(dataset_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    return DatasetSchemaResponse(
        dataset_id=dataset_id,
        schema_summary=session.data_tools.get_schema_summary(),
    )

