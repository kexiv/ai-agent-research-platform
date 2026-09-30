# Research Agent

一个面向 AI 工程研发知识库与工单 Agent。项目用 LangGraph 编排 Agent，用 MCP Python SDK 连接本地 SQLite FTS5 知识库和开发工具，用 Langfuse 观察执行链路，用 DeepEval 做回归评测。

## 当前能力

- FastAPI `POST /chat` 接口。
- LangGraph 路由、检索、工具调用和回答节点。
- SQLite FTS5 本地知识库：支持 Markdown、文本和常见代码文件，提供中文检索与行号引用。
- 本地 MCP Server：`search_knowledge`、`ingest_knowledge`、`search_repo` 和 `get_issue` 工具。
- LangGraph MemorySaver：按 `thread_id` 保存进程内会话状态。
- Langfuse 可选追踪：配置密钥后，Agent 节点自动生成观察记录。
- DeepEval 评测脚本：`python evals/run_eval.py`。

## 启动

需要 Python 3.11+。复制环境变量文件：

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

没有模型密钥时也可以启动。此时系统会使用关键词路由，并返回诊断信息；配置 `OPENAI_API_KEY` 后启用模型路由和答案生成。

启动本地 MCP 工具服务：

```powershell
research-ingest
research-mcp
```

另开终端启动 API：

```powershell
research-agent
```

健康检查：

```powershell
Invoke-RestMethod http://localhost:8000/health
```

调用示例：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/chat `
  -ContentType 'application/json' `
  -Body '{"question":"查询工单 AI-102","thread_id":"demo"}'
```

## 本地知识库

把项目文档、技术方案或代码样例放到 `data/knowledge`，然后重建索引：

```powershell
research-ingest
```

索引文件是生成物 `data/knowledge.db`，已加入 `.gitignore`。Agent 通过 MCP 的 `search_knowledge` 工具查询 SQLite FTS5，不需要 Docker、Elasticsearch、对象存储或独立向量数据库。中文检索会额外生成双字词索引，适合这个作品集项目的轻量演示。

## 接入 Langfuse

配置以下变量即可启用节点追踪：

```text
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000
```

建议后续在 Langfuse 数据集里维护问题、期望答案和版本信息，再比较不同 Prompt、模型和检索参数。

## 运行评测

```powershell
python evals/run_eval.py
```


To Do

1. 为 MCP 工具增加权限、超时、重试和审计字段。
2. 为写操作增加人工确认节点。
3. 把 MemorySaver 替换为可持久化的 checkpoint 存储。
4. 加入 SSE 流式响应和一个简单前端。
5. 如果语料规模变大，再增加 embedding + Chroma/Qdrant 混合检索；保留 FTS5 作为关键词召回和兜底。
