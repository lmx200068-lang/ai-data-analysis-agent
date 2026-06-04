from typing import Any

import pandas as pd
import requests
import streamlit as st

from config import BASE_DIR, SILICONFLOW_MODEL


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


def ensure_state() -> None:
    defaults = {
        "messages": [],
        "source_kind": None,
        "source_id": None,
        "source_summary": None,
        "source_label": None,
        "api_base_url": DEFAULT_API_BASE_URL,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def api_url(path: str) -> str:
    return st.session_state.api_base_url.rstrip("/") + path


def handle_response(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"后端返回了非 JSON 响应：{response.text[:200]}") from exc

    if response.status_code >= 400:
        detail = data.get("detail", data)
        raise RuntimeError(str(detail))

    return data


def api_get(path: str) -> dict[str, Any]:
    response = requests.get(api_url(path), timeout=30)
    return handle_response(response)


def api_post(path: str, json_body: dict[str, Any] | None = None, files=None, timeout: int = 120) -> dict[str, Any]:
    response = requests.post(api_url(path), json=json_body, files=files, timeout=timeout)
    return handle_response(response)


def check_backend() -> bool:
    try:
        api_get("/health")
        return True
    except requests.RequestException:
        return False
    except RuntimeError:
        return False


def set_loaded_source(kind: str, source_id: str, summary: dict[str, Any], label: str) -> None:
    st.session_state.source_kind = kind
    st.session_state.source_id = source_id
    st.session_state.source_summary = summary
    st.session_state.source_label = label
    st.session_state.messages = []


def load_local_csv(path: str) -> None:
    summary = api_post("/datasets/load-local", {"path": path})
    set_loaded_source("csv", summary["dataset_id"], summary, summary["filename"])


def upload_csv(uploaded_file) -> None:
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "text/csv",
        )
    }
    summary = api_post("/datasets/upload", files=files)
    set_loaded_source("csv", summary["dataset_id"], summary, summary["filename"])


def connect_sqlite(path: str) -> None:
    summary = api_post("/databases/connect-sqlite", {"path": path})
    set_loaded_source("sqlite", summary["database_id"], summary, summary["filename"])


def ask_backend(question: str) -> dict[str, Any]:
    source_kind = st.session_state.source_kind
    source_id = st.session_state.source_id

    if source_kind == "csv":
        return api_post(
            "/chat",
            {"dataset_id": source_id, "question": question},
            timeout=180,
        )

    if source_kind == "sqlite":
        return api_post(
            f"/databases/{source_id}/chat",
            {"database_id": source_id, "question": question},
            timeout=180,
        )

    raise RuntimeError("请先加载 CSV 或连接 SQLite 数据库。")


def format_metric_value(value) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def render_chart_specs(charts: list[dict[str, Any]]) -> None:
    for chart in charts:
        chart_type = chart.get("type")
        title = chart.get("title", "图表")
        data = chart.get("data")

        if not data:
            continue

        if chart_type == "metric":
            st.markdown(f"#### {title}")
            cols = st.columns(3)
            for index, item in enumerate(data):
                cols[index % 3].metric(item["label"], format_metric_value(item["value"]))

        if chart_type == "bar":
            df = pd.DataFrame(data)
            x_col = chart.get("x")
            y_col = chart.get("y")

            if x_col in df.columns and y_col in df.columns:
                st.markdown(f"#### {title}")
                st.bar_chart(df.set_index(x_col)[y_col])

        if chart_type == "line":
            df = pd.DataFrame(data)
            x_col = chart.get("x")
            y_col = chart.get("y")

            if x_col in df.columns and y_col in df.columns:
                df[x_col] = pd.to_datetime(df[x_col], errors="coerce")
                df = df.dropna(subset=[x_col])

                if not df.empty:
                    st.markdown(f"#### {title}")
                    st.line_chart(df.set_index(x_col)[y_col])

        if chart_type == "table":
            st.markdown(f"#### {title}")
            st.dataframe(pd.DataFrame(data), use_container_width=True)


def render_tool_calls(tool_calls: list[dict[str, Any]], expanded: bool = False) -> None:
    if not tool_calls:
        return

    with st.expander("工具调用", expanded=expanded):
        for index, tool_call in enumerate(tool_calls, start=1):
            st.markdown(f"**{index}. {tool_call.get('name')}**")
            st.json({
                "args": tool_call.get("args", {}),
                "result": tool_call.get("result", {}),
            })


def show_csv_panel(summary: dict[str, Any]) -> None:
    metric_cols = st.columns(4)
    metric_cols[0].metric("Rows", f"{summary['rows']:,}")
    metric_cols[1].metric("Columns", f"{len(summary['columns']):,}")
    metric_cols[2].metric("Numeric", f"{len(summary['numeric_columns']):,}")
    metric_cols[3].metric("Model", SILICONFLOW_MODEL)

    with st.expander("数据预览", expanded=True):
        st.dataframe(pd.DataFrame(summary["preview"]), use_container_width=True)

    with st.expander("字段信息"):
        st.write("字段：")
        st.write(", ".join(summary["columns"]))
        st.write("数值字段：")
        st.write(", ".join(summary["numeric_columns"]) or "无")
        st.write("类别字段：")
        st.write(", ".join(summary["categorical_columns"]) or "无")


def show_sqlite_panel(summary: dict[str, Any]) -> None:
    database_id = st.session_state.source_id
    tables = summary.get("tables", [])

    metric_cols = st.columns(3)
    metric_cols[0].metric("Tables", f"{len(tables):,}")
    metric_cols[1].metric("Database", summary.get("filename", ""))
    metric_cols[2].metric("Model", SILICONFLOW_MODEL)

    if not tables:
        st.info("这个数据库里没有可用表。")
        return

    table_name = st.selectbox("选择数据表", tables)

    try:
        schema = api_get(f"/databases/{database_id}/tables/{table_name}/schema")
        preview = api_get(f"/databases/{database_id}/tables/{table_name}/preview?limit=20")
    except Exception as exc:
        st.error(f"读取表信息失败：{exc}")
        return

    with st.expander("表预览", expanded=True):
        rows = preview["preview"].get("rows", [])
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with st.expander("表结构"):
        st.dataframe(pd.DataFrame(schema["table_schema"].get("columns", [])), use_container_width=True)


def show_source_panel() -> None:
    summary = st.session_state.source_summary

    if st.session_state.source_kind == "csv":
        show_csv_panel(summary)
        return

    if st.session_state.source_kind == "sqlite":
        show_sqlite_panel(summary)
        return

    st.info("请先在左侧加载 CSV 或连接 SQLite 数据库。")


def get_prompt_buttons() -> list[str]:
    if st.session_state.source_kind == "sqlite":
        return [
            "这个数据库有哪些表？",
            "supermarket_sales 表有哪些字段？",
            "预览 supermarket_sales 表前 5 行",
            "哪个城市销售额最高？",
            "按 Product line 统计总销售额并排序",
            "不同 Payment 的订单数和总销售额是多少？",
        ]

    return [
        "这个超市的核心业务指标怎么样？",
        "按 Product line 分析业务表现",
        "不同 City 的销售表现如何？",
        "每天 Sales 趋势如何？",
        "Sales 和哪些字段相关性最高？",
        "帮我整体分析一下这个超市销售数据",
    ]


def show_chat() -> None:
    st.subheader("对话分析")

    prompt_buttons = get_prompt_buttons()
    cols = st.columns(3)
    selected_prompt = None

    for index, prompt in enumerate(prompt_buttons):
        if cols[index % 3].button(prompt, use_container_width=True):
            selected_prompt = prompt

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            render_chart_specs(message.get("charts", []))
            render_tool_calls(message.get("tool_calls", []))

    user_question = st.chat_input("输入你的数据分析问题")
    question = selected_prompt or user_question

    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("分析中..."):
            try:
                response = ask_backend(question)
                answer = response.get("answer", "")
                charts = response.get("charts", [])
                tool_calls = response.get("tool_calls", [])

                st.write(answer)
                render_chart_specs(charts)
                render_tool_calls(tool_calls, expanded=True)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "charts": charts,
                    "tool_calls": tool_calls,
                })
            except Exception as exc:
                error_message = f"运行出错：{exc}"
                st.error(error_message)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message,
                })


def show_sidebar() -> None:
    with st.sidebar:
        st.header("服务")
        api_base_url = st.text_input("FastAPI 地址", value=st.session_state.api_base_url)
        st.session_state.api_base_url = api_base_url.rstrip("/")

        if check_backend():
            st.success("后端已连接")
        else:
            st.error("后端未连接")
            st.caption("请先运行：uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000")

        st.header("数据源")
        source_kind = st.radio(
            "选择数据源",
            ["CSV", "SQLite"],
            horizontal=True,
        )

        if source_kind == "CSV":
            csv_mode = st.radio("CSV 加载方式", ["本地路径", "上传 CSV"], horizontal=True)

            if csv_mode == "本地路径":
                default_path = str(BASE_DIR / "SuperMarket Analysis.csv")
                csv_path = st.text_input("CSV 路径", value=default_path)

                if st.button("加载 CSV", type="primary", use_container_width=True):
                    try:
                        load_local_csv(csv_path)
                        st.success("CSV 已加载")
                    except Exception as exc:
                        st.error(f"加载失败：{exc}")

            if csv_mode == "上传 CSV":
                uploaded_file = st.file_uploader("上传 CSV 文件", type=["csv"])

                if st.button("上传并加载", type="primary", use_container_width=True):
                    if uploaded_file is None:
                        st.warning("请先选择 CSV 文件。")
                    else:
                        try:
                            upload_csv(uploaded_file)
                            st.success("CSV 已上传并加载")
                        except Exception as exc:
                            st.error(f"上传失败：{exc}")

        if source_kind == "SQLite":
            default_db = str(BASE_DIR / "supermarket_demo.db")
            sqlite_path = st.text_input("SQLite 路径", value=default_db)

            if st.button("连接 SQLite", type="primary", use_container_width=True):
                try:
                    connect_sqlite(sqlite_path)
                    st.success("SQLite 已连接")
                except Exception as exc:
                    st.error(f"连接失败：{exc}")

        if st.session_state.source_id:
            st.divider()
            st.caption(f"当前数据源：{st.session_state.source_label}")

            if st.button("清空对话", use_container_width=True):
                st.session_state.messages = []


def main() -> None:
    st.set_page_config(
        page_title="多源数据分析 Agent",
        page_icon="📊",
        layout="wide",
    )

    ensure_state()

    st.title("多源数据分析 Agent")
    st.caption("Streamlit 前端 → FastAPI 后端 → LangChain Agent → CSV / SQLite 工具")

    show_sidebar()

    if not st.session_state.source_id:
        st.info("请先在左侧加载 CSV 或连接 SQLite 数据库。")
        return

    st.caption(f"当前数据源：{st.session_state.source_label}")

    left, right = st.columns([1, 1])

    with left:
        show_source_panel()

    with right:
        show_chat()


if __name__ == "__main__":
    main()
