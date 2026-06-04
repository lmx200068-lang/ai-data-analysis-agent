from openai import OpenAI

from config import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL, validate_config


def create_client() -> OpenAI:
    validate_config()
    return OpenAI(
        api_key=SILICONFLOW_API_KEY,
        base_url=SILICONFLOW_BASE_URL,
    )