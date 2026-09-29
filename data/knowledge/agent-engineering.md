# Agent Engineering 项目知识库

## 项目目标

这是一个面向 AI 工程岗位作品集的研发知识库与工单 Agent。核心链路使用 LangGraph 编排路由、知识检索、MCP 工具调用和最终回答；MCP Server 暴露可发现、可审计的工具。

## SQLite FTS5 检索

本项目使用 SQLite FTS5 保存本地知识库索引。原始文档放在 data/knowledge，执行 research-ingest 后生成 data/knowledge.db。索引按约 1200 字符切块并保留 150 字符重叠，同时记录来源文件和起止行号。中文查询会增加双字词索引，避免完全依赖英文分词器。

## MCP 工具设计

search_knowledge 用于查询本地知识库，ingest_knowledge 用于重建索引，search_repo 用于搜索代码，get_issue 用于查询工单。工具参数应有明确的 schema，调用失败时要返回可解释错误，并由 Agent 决定是否降级。

## 评测与观测

Langfuse 用于记录路由、检索、工具调用和回答节点的执行链路。DeepEval 用于评测答案相关性、上下文利用和引用质量。可持续记录 Recall@5、引用命中率、工具选择准确率、P95 延迟和模型成本。

## 面试可展示点

重点展示可恢复的索引构建、中文检索、MCP 工具发现、超时与降级、结构化 citation、LangGraph 状态流转，以及从原型到稳定工程服务的演进过程。
