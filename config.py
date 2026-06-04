import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "").strip()
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3").strip()
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").strip()

DEFAULT_CSV_PATH = BASE_DIR / "sample_sales.csv"


def validate_config() -> None:
    if not SILICONFLOW_API_KEY:
        raise ValueError("Missing SILICONFLOW_API_KEY. Please check your .env file.")