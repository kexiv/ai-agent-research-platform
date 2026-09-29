# AI Agent 项目简历经历

## 项目一 AI 研发知识库与工单 Agent

**项目角色：** AI Agent 工程 / 独立开发
**项目时间：** 2026.09 - 至今
**技术栈：** Python、LangGraph、MCP Python SDK、SQLite FTS5、FastAPI、OpenAI-compatible API、Langfuse、DeepEval、Docker Compose

面向研发文档、代码和工单查询场景，设计并实现轻量、可观测、可评测的 Agent 应用。

- 使用 LangGraph 编排路由、知识检索、MCP 工具调用和回答节点，按 `knowledge / repo / issue / direct` 四类意图分流，并通过 `thread_id` 维护会话状态。
- 使用 MCP Python SDK 实现工具发现与调用，提供知识检索、索引重建、代码搜索和工单查询工具；统一处理模型、检索和工具调用的超时、失败与降级回答。
- 使用 SQLite FTS5 构建本地知识库，支持 Markdown、文本和常见代码文件；实现 1200 字符切分、150 字符重叠、BM25 排序、中文双字词检索和来源行号记录。
- 使用 FastAPI 提供 `/chat`、`/health` 接口，通过 Docker Compose 编排 API 与 MCP 服务，并补充中文检索测试和 MCP 容器健康检查。
- 支持可选 Langfuse 节点追踪和 DeepEval 回归评测脚本，覆盖答案相关性、Faithfulness、引用质量和工具选择等质量维度。

**招聘网站精简版：** 独立开发 AI 研发知识库与工单 Agent，基于 LangGraph 编排意图路由、SQLite FTS5 检索、MCP 工具调用和回答生成；实现中文双字词检索、来源与行号 citation、工具超时降级及 FastAPI 接口，并接入 Langfuse、DeepEval 完成可观测和质量评测闭环。

## 项目二 Enterprise RAG Knowledge Platform

**项目角色：** RAG / AI Agent 工程 / 独立开发
**项目时间：** 2026.09 - 至今
**技术栈：** Python、LangGraph、MCP Python SDK、FastAPI、PostgreSQL、pgvector、FastEmbed、Redis、Mimo OpenAI-compatible API、Docker Compose

面向企业文档、工单和代码知识库场景，搭建从本地 SQLite 到 PostgreSQL + pgvector 的可演进 RAG 平台。

- 设计文档导入、切分、Embedding、元数据保存和引用返回链路，保留来源文件、标题、起止行号和摘要信息。
- 使用 FastEmbed `BAAI/bge-small-zh-v1.5` 生成 512 维向量，结合 PostgreSQL `tsvector`、pgvector 余弦相似度和 RRF 融合，兼顾错误码、工单号等精确术语与自然语言语义召回。
- 基于 LangGraph 编排检索与回答流程，使用 MCP 暴露知识检索、文档导入和工单查询工具，通过 OpenAI-compatible API 接入 Mimo 模型。
- 使用 FastAPI 提供 `/health`、`/search`、`/chat`、`/documents/ingest` 接口，完成 PostgreSQL、pgvector、FastEmbed 和 Redis Compose 环境验证。
- 完成 4 个单元测试，以及真实文档导入、混合检索和带引用回答验证，返回结果可追溯到 `engineering-handbook.md:1-18`。

**招聘网站精简版：** 独立开发 Enterprise RAG Knowledge Platform，基于 LangGraph、MCP、FastAPI、PostgreSQL + pgvector 和 FastEmbed 构建企业知识库；实现文档导入、512 维向量检索、关键词与向量 RRF 融合、引用返回、Mimo 模型接入及 Docker Compose 部署。

## 面试展开关键词

- 为什么同时保留两个项目：第一个突出轻量 Agent、MCP 和 FTS5 原理；第二个突出 PostgreSQL、pgvector、Embedding、混合检索和容器化工程能力。
- 如何处理中文检索：第一个项目在索引侧和查询侧使用一致的中文双字词展开逻辑；第二个项目通过向量召回补充关键词检索的语义覆盖。
- 如何保证回答可验证：检索结果保留来源、行号和内容片段，回答节点仅基于证据生成，并在证据不足时明确拒答或降级。
- 如何保证 Agent 稳定性：在模型、检索和 MCP 工具边界设置超时，使用结构化错误处理和降级回答避免单个依赖失败拖垮整条链路。
- 下一步演进：补充企业权限过滤、Redis 结果缓存、可持久化 checkpoint、Recall@5、引用命中率、P95 延迟和成本指标。
