import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from config import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL, SILICONFLOW_MODEL
from data_tools import CsvDataTools


SYSTEM_PROMPT = (
    "You are a careful CSV data analysis agent. "
    "Use tools for concrete calculations instead of guessing. "
    "Answer in Chinese. Keep answers concise and mention the computed evidence. "
    "Do not confuse frequency with sales amount. "
    "If you say a category is popular, specify whether it is based on count or Sales."
)


class LangChainPandasAgent:
    def __init__(self, data_tools: CsvDataTools):
        self.data_tools = data_tools
        self.chat_history = []
        self.last_tool_calls = []
        self.tools = self._build_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.model = ChatOpenAI(
            model=SILICONFLOW_MODEL,
            api_key=SILICONFLOW_API_KEY,
            base_url=SILICONFLOW_BASE_URL,
            temperature=0.1,
            max_tokens=900,
        )

    def ask(self, user_question: str) -> str:
        self.last_tool_calls = []
        schema = self.data_tools.get_schema_summary()

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content="Current CSV schema:\n" + json.dumps(schema, ensure_ascii=False, default=str)),
            *self.chat_history[-6:],
            HumanMessage(content=user_question),
        ]

        tool_choice = self._choose_tool_choice(user_question)
        first_model = self.model.bind_tools(self.tools, tool_choice=tool_choice)
        assistant_message = first_model.invoke(messages)
        messages.append(assistant_message)

        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args") or {}

                if tool_name not in self.tool_map:
                    raise ValueError(f"Unknown LangChain tool: {tool_name}")

                tool_result = self.tool_map[tool_name].invoke(tool_args)

                messages.append(
                    ToolMessage(
                        content=json.dumps(tool_result, ensure_ascii=False, default=str),
                        tool_call_id=tool_call["id"],
                        name=tool_name,
                    )
                )

            final_message = self.model.invoke(messages)
            answer = str(final_message.content or "")
        else:
            answer = str(assistant_message.content or "")

        self.chat_history.append(HumanMessage(content=user_question))
        self.chat_history.append(AIMessage(content=answer))
        return answer

    def _record_tool_result(self, name: str, args: dict, result: dict) -> dict:
        self.last_tool_calls.append({
            "name": name,
            "args": args,
            "result": result,
        })
        print(f"\n[Tool] {name}")
        print(f"[Args] {json.dumps(args, ensure_ascii=False)}")
        print(f"[Result] {json.dumps(result, ensure_ascii=False, indent=2, default=str)}")
        return result

    def _choose_tool_choice(self, user_question: str):
        question = user_question.lower()

        if any(keyword in question for keyword in ["趋势", "日期", "每天", "每日", "按天", "每周", "每月", "时间", "trend", "daily", "weekly", "monthly", "date", "time", "哪一天", "哪天", "最高一天", "最高日期"]):
            return "time_trend"

        if any(keyword in question for keyword in ["相关", "相关性", "correlation", "correlated", "relationship", "related"]):
            return "correlation_report"

        if any(keyword in question for keyword in ["kpi", "指标", "业绩", "经营", "业务概览", "销售概览", "核心业务"]):
            if any(keyword in question for keyword in ["比较", "对比", "不同", "各", "按", "by", "compare", "comparison"]):
                return "category_performance"
            return "business_kpi_overview"

        if any(keyword in question for keyword in ["不同", "各", "按", "分组", "对比", "表现", "客单价", "产品线", "城市", "支付", "会员", "性别", "by", "compare", "comparison", "performance", "product line", "city", "payment", "customer type", "gender", "branch"]):
            return "category_performance"

        if any(keyword in question for keyword in ["整体", "总体", "全面", "概览", "eda", "探索性"]):
            return "eda_overview"

        if any(keyword in question for keyword in ["缺失", "空值", "null", "missing", "重复", "duplicate"]):
            return "missing_report"

        if any(keyword in question for keyword in ["所有数值", "全部数值", "数值字段", "数值列", "描述统计", "numeric"]):
            return "numeric_summary"

        if any(keyword in question for keyword in ["所有类别", "全部类别", "类别字段", "类别列", "分类字段", "categorical"]):
            return "categorical_summary"

        return "auto"

    def _build_tools(self):
        def get_schema_summary() -> dict:
            """Inspect the CSV table schema, column types, missing values, and sample rows."""
            result = self.data_tools.get_schema_summary()
            return self._record_tool_result("get_schema_summary", {}, result)

        def groupby_sum(group_col: str, value_col: str, top_n: int = 5) -> dict:
            """Group by one column and sum a numeric column."""
            args = {"group_col": group_col, "value_col": value_col, "top_n": top_n}
            result = self.data_tools.groupby_sum(**args)
            return self._record_tool_result("groupby_sum", args, result)

        def sum_column(column: str) -> dict:
            """Calculate the total sum of a numeric column."""
            args = {"column": column}
            result = self.data_tools.sum_column(**args)
            return self._record_tool_result("sum_column", args, result)

        def describe_column(column: str) -> dict:
            """Describe a numeric or categorical column."""
            args = {"column": column}
            result = self.data_tools.describe_column(**args)
            return self._record_tool_result("describe_column", args, result)

        def count_by_column(column: str, top_n: int = 10) -> dict:
            """Count the frequency of values in a categorical column."""
            args = {"column": column, "top_n": top_n}
            result = self.data_tools.count_by_column(**args)
            return self._record_tool_result("count_by_column", args, result)

        def missing_report() -> dict:
            """Analyze missing values and duplicate rows in the CSV dataset."""
            result = self.data_tools.missing_report()
            return self._record_tool_result("missing_report", {}, result)

        def numeric_summary() -> dict:
            """Summarize all numeric columns with descriptive statistics."""
            result = self.data_tools.numeric_summary()
            return self._record_tool_result("numeric_summary", {}, result)

        def categorical_summary(top_n: int = 5) -> dict:
            """Summarize categorical columns with unique counts and top frequent values."""
            args = {"top_n": top_n}
            result = self.data_tools.categorical_summary(**args)
            return self._record_tool_result("categorical_summary", args, result)

        def correlation_report(target_col: str = "", top_n: int = 10) -> dict:
            """Analyze Pearson correlations between numeric columns or with a target column."""
            target = target_col or None
            args = {"target_col": target, "top_n": top_n}
            result = self.data_tools.correlation_report(**args)
            return self._record_tool_result("correlation_report", args, result)

        def eda_overview() -> dict:
            """Run complete EDA: schema, missing values, numeric summary, categorical summary, and correlations."""
            result = self.data_tools.eda_overview()
            return self._record_tool_result("eda_overview", {}, result)

        def business_kpi_overview(
            sales_col: str = "Sales",
            quantity_col: str = "Quantity",
            profit_col: str = "gross income",
            rating_col: str = "Rating",
        ) -> dict:
            """Calculate total sales, order count, AOV, quantity, profit, and rating."""
            args = {
                "sales_col": sales_col,
                "quantity_col": quantity_col,
                "profit_col": profit_col,
                "rating_col": rating_col,
            }
            result = self.data_tools.business_kpi_overview(**args)
            return self._record_tool_result("business_kpi_overview", args, result)

        def category_performance(
            group_col: str,
            sales_col: str = "Sales",
            quantity_col: str = "Quantity",
            profit_col: str = "gross income",
            rating_col: str = "Rating",
            top_n: int = 10,
        ) -> dict:
            """Analyze business performance by a categorical column such as City, Product line, or Payment."""
            args = {
                "group_col": group_col,
                "sales_col": sales_col,
                "quantity_col": quantity_col,
                "profit_col": profit_col,
                "rating_col": rating_col,
                "top_n": top_n,
            }
            result = self.data_tools.category_performance(**args)
            return self._record_tool_result("category_performance", args, result)

        def time_trend(
            date_col: str = "Date",
            value_col: str = "Sales",
            freq: str = "D",
            top_n: int = 10,
        ) -> dict:
            """Analyze sales or another numeric value over time."""
            args = {"date_col": date_col, "value_col": value_col, "freq": freq, "top_n": top_n}
            result = self.data_tools.time_trend(**args)
            return self._record_tool_result("time_trend", args, result)

        functions = [
            get_schema_summary,
            groupby_sum,
            sum_column,
            describe_column,
            count_by_column,
            missing_report,
            numeric_summary,
            categorical_summary,
            correlation_report,
            eda_overview,
            business_kpi_overview,
            category_performance,
            time_trend,
        ]
        return [StructuredTool.from_function(func=func) for func in functions]
