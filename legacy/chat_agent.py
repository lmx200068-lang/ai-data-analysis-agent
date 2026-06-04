from pathlib import Path

from legacy.agent import PandasAgent
from config import DEFAULT_CSV_PATH, SILICONFLOW_MODEL
from data_tools import CsvDataTools
from llm import create_client


def ask_csv_path() -> Path:
    user_input = input(f"请输入 CSV 文件路径，直接回车使用默认文件 {DEFAULT_CSV_PATH.name}：").strip()

    if not user_input:
        return DEFAULT_CSV_PATH

    user_input = user_input.strip('"').strip("'")
    csv_path = Path(user_input)

    if not csv_path.is_absolute():
        csv_path = Path(__file__).parent / csv_path

    return csv_path


def main() -> None:
    csv_path = ask_csv_path()
    data_tools = CsvDataTools(csv_path)
    client = create_client()
    agent = PandasAgent(client, data_tools)

    print("\nCSV 数据分析 Agent 已启动")
    print(f"模型: {SILICONFLOW_MODEL}")
    print(f"当前数据文件: {csv_path}")
    print(f"字段: {', '.join(data_tools.df.columns)}")
    print("输入 exit / quit / q 可以退出。\n")

    while True:
        user_question = input("你：").strip()

        if user_question.lower() in {"exit", "quit", "q"}:
            print("Agent：已退出。")
            break

        if not user_question:
            continue

        try:
            answer = agent.ask(user_question)
            print(f"\nAgent：{answer}\n")
        except Exception as exc:
            print(f"\nAgent：运行出错：{exc}\n")


if __name__ == "__main__":
    main()