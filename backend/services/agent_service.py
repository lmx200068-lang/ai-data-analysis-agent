import contextlib
import io
from typing import Any


def ask_agent(session, question: str) -> tuple[str, list[dict[str, Any]], str]:
    buffer = io.StringIO()

    with contextlib.redirect_stdout(buffer):
        answer = session.agent.ask(question)

    tool_calls = list(getattr(session.agent, "last_tool_calls", []))
    tool_log = buffer.getvalue().strip()
    return answer, tool_calls, tool_log


def build_chart_specs(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    charts = []

    for tool_call in tool_calls:
        name = tool_call.get("name")
        result = tool_call.get("result") or {}

        if not isinstance(result, dict) or "error" in result:
            continue

        if name == "business_kpi_overview":
            metrics = []
            metric_keys = [
                ("总销售额", "total_sales"),
                ("订单数", "order_count"),
                ("平均客单价", "avg_order_value"),
                ("总销量", "total_quantity"),
                ("总利润", "total_profit"),
                ("平均评分", "avg_rating"),
            ]

            for label, key in metric_keys:
                if key in result:
                    metrics.append({"label": label, "value": result[key]})

            charts.append({
                "type": "metric",
                "title": "KPI 指标",
                "data": metrics,
            })

        if name == "category_performance":
            rows = result.get("result", [])
            group_col = result.get("group_col")

            if rows and group_col:
                charts.append({
                    "type": "bar",
                    "title": "分组销售额",
                    "data": rows,
                    "x": group_col,
                    "y": "total_sales",
                })
                charts.append({
                    "type": "table",
                    "title": "分组明细数据",
                    "data": rows,
                })

        if name == "time_trend":
            rows = result.get("trend", []) or result.get("trend_sample", [])

            if rows:
                charts.append({
                    "type": "line",
                    "title": "时间趋势",
                    "data": rows,
                    "x": "period",
                    "y": "total_value",
                })

            top_periods = result.get("top_periods", [])
            if top_periods:
                charts.append({
                    "type": "table",
                    "title": "销售额最高日期",
                    "data": top_periods,
                })

        if name == "correlation_report":
            correlations = result.get("correlations")
            if correlations:
                rows = [{"column": key, "correlation": value} for key, value in correlations.items()]
                charts.append({
                    "type": "bar",
                    "title": "相关性",
                    "data": rows,
                    "x": "column",
                    "y": "correlation",
                })

            pairs = result.get("correlation_pairs")
            if pairs:
                rows = [
                    {
                        "pair": f"{item['column_a']} / {item['column_b']}",
                        "correlation": item["correlation"],
                    }
                    for item in pairs
                ]
                charts.append({
                    "type": "bar",
                    "title": "相关性",
                    "data": rows,
                    "x": "pair",
                    "y": "correlation",
                })

        if name in {"run_readonly_query", "preview_table"}:
            rows = result.get("rows", [])

            if rows:
                charts.append({
                    "type": "table",
                    "title": "查询结果",
                    "data": rows,
                })

                first_row = rows[0]
                string_columns = [key for key, value in first_row.items() if isinstance(value, str)]
                numeric_columns = [key for key, value in first_row.items() if isinstance(value, (int, float))]

                if string_columns and numeric_columns:
                    charts.append({
                        "type": "bar",
                        "title": "查询结果图表",
                        "data": rows,
                        "x": string_columns[0],
                        "y": numeric_columns[0],
                    })

    return charts
