from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from config import BASE_DIR
from data_tools import CsvDataTools
from langchain_agent import LangChainPandasAgent


UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@dataclass
class DatasetSession:
    dataset_id: str
    csv_path: Path
    data_tools: CsvDataTools
    agent: LangChainPandasAgent


class DatasetStore:
    def __init__(self) -> None:
        self._sessions: dict[str, DatasetSession] = {}

    def list_datasets(self) -> list[DatasetSession]:
        return list(self._sessions.values())

    def get(self, dataset_id: str) -> DatasetSession | None:
        return self._sessions.get(dataset_id)

    def create_from_path(self, csv_path: Path) -> DatasetSession:
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        data_tools = CsvDataTools(csv_path)
        session = DatasetSession(
            dataset_id=str(uuid4()),
            csv_path=csv_path,
            data_tools=data_tools,
            agent=LangChainPandasAgent(data_tools),
        )
        self._sessions[session.dataset_id] = session
        return session

    def save_upload(self, filename: str, content: bytes) -> DatasetSession:
        safe_name = self._clean_filename(filename)
        csv_path = UPLOAD_DIR / f"{uuid4().hex}_{safe_name}"
        csv_path.write_bytes(content)
        return self.create_from_path(csv_path)

    @staticmethod
    def to_summary(session: DatasetSession) -> dict:
        df = session.data_tools.df
        return {
            "dataset_id": session.dataset_id,
            "filename": session.csv_path.name,
            "rows": len(df),
            "columns": list(df.columns),
            "numeric_columns": list(df.select_dtypes(include="number").columns),
            "categorical_columns": list(df.select_dtypes(include=["object", "category", "bool"]).columns),
            "preview": df.head(10).to_dict(orient="records"),
        }

    @staticmethod
    def _clean_filename(filename: str) -> str:
        keep = []
        for char in filename.strip():
            if char.isalnum() or char in {".", "_", "-", " "}:
                keep.append(char)
            else:
                keep.append("_")
        return "".join(keep) or "uploaded.csv"


dataset_store = DatasetStore()
