# Multi-Source Data Analysis Agent

一个面向业务数据的本地多源智能分析 Agent 原型。项目主线是 React 前端、FastAPI 后端、LangChain 工具调用，以及 CSV / SQLite 两类数据源的真实计算分析。

## 功能亮点

- 加载本地 CSV 或上传 CSV 文件
- 连接本地 SQLite 数据库
- 查看字段、表结构和数据预览
- 用自然语言提问数据问题
- 由 LLM 选择 pandas / SQL 工具完成真实计算
- 返回中文分析、工具调用记录和基础图表
- SQLite 查询默认只读，阻止 destructive SQL
- BLOB 字段会转换为 `<BLOB n bytes>`，避免 JSON 序列化失败

## 技术栈

- Python, pandas, SQLite
- FastAPI, Pydantic
- LangChain, OpenAI-compatible API
- React, Vite
- Streamlit prototype

## 项目结构

```text
data_agent/
├─ backend/                  # FastAPI backend
│  ├─ main.py
│  ├─ schemas.py
│  ├─ routes/
│  └─ services/
├─ frontend/                 # React + Vite frontend
│  ├─ package.json
│  ├─ vite.config.js
│  └─ src/
├─ legacy/                   # Early prototype scripts
├─ scripts/
│  └─ create_demo_sqlite.py
├─ config.py
├─ data_tools.py             # CSV / pandas tools
├─ langchain_agent.py        # CSV Agent
├─ sql_tools.py              # SQLite tools
├─ sql_agent.py              # SQLite Agent
├─ chat_langchain_agent.py   # CLI debug entry
├─ streamlit_app.py          # Streamlit prototype
├─ requirements.txt
├─ sample_sales.csv
└─ SuperMarket Analysis.csv
```

## 环境配置

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

然后在 `.env` 中填写自己的 API Key：

```text
SILICONFLOW_API_KEY=your_api_key_here
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V3
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

安装 Python 依赖：

```powershell
pip install -r requirements.txt
```

安装前端依赖：

```powershell
cd frontend
npm install
```

## 运行方式

启动 FastAPI 后端：

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

生成示例 SQLite 数据库：

```powershell
python scripts/create_demo_sqlite.py
```

启动 React 前端：

```powershell
cd frontend
npm run dev
```

默认前端地址：

```text
http://localhost:5173
```

## 示例问题

CSV 数据：

```text
这个超市的核心业务指标怎么样？
不同 City 的销售表现如何？
每天 Sales 趋势如何？
Sales 和哪些字段相关性最高？
帮我整体分析一下这个超市销售数据
```

SQLite 数据：

```text
这个数据库有哪些表？
supermarket_sales 表有哪些字段？
预览 supermarket_sales 表前 5 行
哪个城市销售额最高？
按 Product line 统计总销售额并排序
```

## Agent 工作机制

```text
用户问题
  ↓
FastAPI 接收请求并读取数据源上下文
  ↓
LangChain ChatOpenAI + bind_tools 选择工具
  ↓
pandas / SQLite 工具执行真实计算
  ↓
工具结果返回给 LLM 生成中文分析
  ↓
前端展示答案、工具调用记录和图表
```

LLM 负责理解问题和组织表达，工具层负责真实计算，后端负责调度和安全控制。

## 安全边界

SQLite Agent 只允许 `SELECT` 和 `WITH` 查询，并阻止下列 SQL 操作：

```text
INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, REPLACE,
TRUNCATE, ATTACH, DETACH, PRAGMA, VACUUM
```

`.env`、上传文件、缓存、SQLite 数据库和前端依赖目录都已加入 `.gitignore`。

## 当前状态

这是一个本地 Demo / MVP，适合作为 AI Agent 产品和开发作品基础。当前重点是展示多源数据接入、工具调用、真实计算、只读 SQL 安全控制和前后端产品化形态。

## 后续规划

- 数据源 Adapter 抽象：统一 schema / preview / summary / query
- Excel / MySQL / API 数据源
- LangGraph 多步分析工作流
- 更完整的图表规格和可视化渲染
- 用户会话管理与分析日志
- 自动生成分析报告并导出
