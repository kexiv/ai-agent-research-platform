# 研发知识库与工单 Agent 路线图

## Milestone 1：能跑

- API、LangGraph、MCP Server 和 MCP Client 连接起来。
- 没有外部密钥时也能返回可诊断结果。
- 完成 `search_repo` 和 `get_issue` 两个只读工具。

## Milestone 2：能用

- 接入 SQLite FTS5 本地知识库，并通过 MCP 暴露检索和索引工具。
- 支持引用来源和无证据拒答。
- 支持多轮 thread 和工具失败后的降级。

## Milestone 3：可评测

- Langfuse 记录路由、检索、工具和模型节点。
- DeepEval 覆盖答案相关性、Faithfulness、工具选择和任务完成度。
- 用同一数据集比较 Prompt、模型和检索参数。

## Milestone 4：像生产系统

- 工具权限、参数校验、超时、重试、幂等和审计。
- 写操作前人工确认。
- 持久化 checkpoint、SSE 流式输出、Docker Compose 和 README 演示。
