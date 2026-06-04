import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
model = os.getenv("SILICONFLOW_MODEL", "Pro/Qwen/Qwen2.5-7B-Instruct").strip()

if not api_key:
    raise ValueError("没有读取到 SILICONFLOW_API_KEY，请检查 .env 文件。")

print("API Key 前缀:", api_key[:5])
print("API Key 后缀:", api_key[-4:])
print("API Key 长度:", len(api_key))
print("模型:", model)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.siliconflow.cn/v1",
)

response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "你是一个简洁、严谨的中文助手。"},
        {"role": "user", "content": "用三句话解释什么是 AI Agent。"},
    ],
    temperature=0.3,
)

print(response.choices[0].message.content)