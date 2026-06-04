import json

from config import SILICONFLOW_MODEL
from data_tools import TOOLS_SCHEMA, CsvDataTools


class PandasAgent:
    def __init__(self, client, data_tools: CsvDataTools):
        self.client = client
        self.data_tools = data_tools
        self.chat_history = []
        self.last_tool_calls = []

    def ask(self, user_question: str) -> str:
        self.last_tool_calls = []
        schema = self.data_tools.get_schema_summary()

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a careful data analysis agent. "
                    "Do not guess concrete data results. "
                    "When the user asks about missing values, duplicate rows, numeric summaries, categorical summaries, correlations, or an overall dataset analysis, you must use the matching tool. "
                    "For overall analysis, prefer eda_overview. "
                    "Do not confuse frequency with sales amount. A category with the highest count is not necessarily the category with the highest Sales. "
                    "Do not confuse frequency with sales amount. If you say a category is popular, specify whether it is based on count or Sales. "
                    "Answer in Chinese. Keep the answer concise and mention the computed evidence."
                ),
            },
            {
                "role": "user",
                "content": "Current CSV schema:\n"
                + json.dumps(schema, ensure_ascii=False, indent=2, default=str),
            },
        ]

        messages.extend(self.chat_history[-6:])
        messages.append({"role": "user", "content": user_question})

        first_response = self.client.chat.completions.create(
            model=SILICONFLOW_MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice=self._choose_tool_choice(user_question),
            temperature=0.1,
            max_tokens=800,
        )

        assistant_message = first_response.choices[0].message
        messages.append(assistant_message.model_dump(exclude_none=True))

        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments or "{}")
                tool_result = self.data_tools.call_tool(tool_name, tool_args)
                self.last_tool_calls.append({
                    "name": tool_name,
                    "args": tool_args,
                    "result": tool_result,
                })

                print(f"\n[Tool] {tool_name}")
                print(f"[Args] {json.dumps(tool_args, ensure_ascii=False)}")
                print(f"[Result] {json.dumps(tool_result, ensure_ascii=False, indent=2, default=str)}")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                    }
                )

            final_response = self.client.chat.completions.create(
                model=SILICONFLOW_MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                temperature=0.1,
                max_tokens=800,
            )

            answer = final_response.choices[0].message.content or ""
        else:
            answer = assistant_message.content or ""

        self.chat_history.append({"role": "user", "content": user_question})
        self.chat_history.append({"role": "assistant", "content": answer})

        return answer
    def _choose_tool_choice(self, user_question: str):
        question = user_question.lower()

        if any(keyword in question for keyword in ["趋势", "日期", "每天", "每日", "按天", "每周", "每月", "时间", "trend"]):
            return {"type": "function", "function": {"name": "time_trend"}}

        if any(keyword in question for keyword in ["kpi", "指标", "业绩", "经营", "业务概览", "销售概览", "核心业务"]):
            return {"type": "function", "function": {"name": "business_kpi_overview"}}

        if any(keyword in question for keyword in ["不同", "各", "按", "分组", "对比", "表现", "客单价", "产品线", "城市", "支付", "会员", "性别"]):
            return {"type": "function", "function": {"name": "category_performance"}}
        if any(keyword in question for keyword in ["整体", "总体", "全面", "概览", "eda", "探索性"]):
            return {"type": "function", "function": {"name": "eda_overview"}}

        if any(keyword in question for keyword in ["缺失", "空值", "null", "missing", "重复", "duplicate"]):
            return {"type": "function", "function": {"name": "missing_report"}}

        if any(keyword in question for keyword in ["相关", "相关性", "correlation"]):
            return {"type": "function", "function": {"name": "correlation_report"}}

        if any(keyword in question for keyword in ["所有数值", "全部数值", "数值字段", "数值列", "描述统计", "numeric"]):
            return {"type": "function", "function": {"name": "numeric_summary"}}

        if any(keyword in question for keyword in ["所有类别", "全部类别", "类别字段", "类别列", "分类字段", "categorical"]):
            return {"type": "function", "function": {"name": "categorical_summary"}}

        return "auto"