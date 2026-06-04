import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from config import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL, SILICONFLOW_MODEL
from sql_tools import SQLiteDataTools


SYSTEM_PROMPT = (
    "You are a careful SQLite data analysis agent. "
    "Use tools for database inspection and SQL analysis. "
    "Only use read-only SELECT/WITH queries. "
    "Never request destructive SQL operations. "
    "Answer in Chinese and mention the computed evidence."
)


class SQLiteAgent:
    def __init__(self, sql_tools: SQLiteDataTools):
        self.sql_tools = sql_tools
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

    def ask(self, question: str) -> str:
        self.last_tool_calls = []
        db_summary = self.sql_tools.database_summary()
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content="Current SQLite database summary:\n" + json.dumps(db_summary, ensure_ascii=False, default=str)),
            *self.chat_history[-6:],
            HumanMessage(content=question),
        ]

        first_model = self.model.bind_tools(self.tools, tool_choice=self._choose_tool_choice(question))
        assistant_message = first_model.invoke(messages)
        messages.append(assistant_message)

        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args") or {}

                if tool_name not in self.tool_map:
                    raise ValueError(f"Unknown SQLite tool: {tool_name}")

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

        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=answer))
        return answer

    def _record_tool_result(self, name: str, args: dict, result: dict) -> dict:
        self.last_tool_calls.append({"name": name, "args": args, "result": result})
        print(f"\n[SQL Tool] {name}")
        print(f"[Args] {json.dumps(args, ensure_ascii=False)}")
        print(f"[Result] {json.dumps(result, ensure_ascii=False, indent=2, default=str)}")
        return result

    def _choose_tool_choice(self, question: str):
        lowered = question.lower()

        if any(keyword in lowered for keyword in ["有哪些表", "list tables", "tables", "表"]):
            if not any(keyword in lowered for keyword in ["字段", "schema", "结构", "预览", "preview", "分析", "查询"]):
                return "list_tables"

        if any(keyword in lowered for keyword in ["字段", "schema", "结构"]):
            return "get_table_schema"

        if any(keyword in lowered for keyword in ["预览", "preview", "前几行", "sample"]):
            return "preview_table"

        if any(keyword in lowered for keyword in ["概览", "整体", "summary", "database"]):
            return "database_summary"

        if any(keyword in lowered for keyword in ["查询", "分析", "销售", "销售额", "最高", "最低", "平均", "总计", "数量", "分组", "排序", "query", "analyze", "sales", "highest", "lowest", "average", "sum", "count", "group by", "order by"]):
            return "run_readonly_query"

        return "auto"

    def _build_tools(self):
        def list_tables() -> dict:
            """List all user tables in the SQLite database."""
            result = self.sql_tools.list_tables()
            return self._record_tool_result("list_tables", {}, result)

        def get_table_schema(table_name: str) -> dict:
            """Get schema information for one SQLite table."""
            args = {"table_name": table_name}
            result = self.sql_tools.get_table_schema(**args)
            return self._record_tool_result("get_table_schema", args, result)

        def preview_table(table_name: str, limit: int = 10) -> dict:
            """Preview rows from a SQLite table."""
            args = {"table_name": table_name, "limit": limit}
            result = self.sql_tools.preview_table(**args)
            return self._record_tool_result("preview_table", args, result)

        def run_readonly_query(sql: str, limit: int = 100) -> dict:
            """Run a safe read-only SELECT/WITH SQL query with a row limit."""
            args = {"sql": sql, "limit": limit}
            result = self.sql_tools.run_readonly_query(**args)
            return self._record_tool_result("run_readonly_query", args, result)

        def table_summary(table_name: str) -> dict:
            """Summarize one SQLite table with row count, schema, and sample rows."""
            args = {"table_name": table_name}
            result = self.sql_tools.table_summary(**args)
            return self._record_tool_result("table_summary", args, result)

        def database_summary() -> dict:
            """Summarize the full SQLite database with all tables."""
            result = self.sql_tools.database_summary()
            return self._record_tool_result("database_summary", {}, result)

        return [
            StructuredTool.from_function(func=list_tables),
            StructuredTool.from_function(func=get_table_schema),
            StructuredTool.from_function(func=preview_table),
            StructuredTool.from_function(func=run_readonly_query),
            StructuredTool.from_function(func=table_summary),
            StructuredTool.from_function(func=database_summary),
        ]
