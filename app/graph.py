from __future__ import annotations

import json
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.llm import LLMError, OpenAICompatibleClient
from app.mcp.client import MCPClient, MCPError
from app.models import AgentState
from app.observability import observe


llm = OpenAICompatibleClient()
settings = get_settings()


def _add_step(state: AgentState, step: str) -> list[str]:
    return [*state.get("steps", []), step]


def _parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


@observe("agent.route")
async def route_node(state: AgentState) -> AgentState:
    question = state["question"]
    intent = "direct"
    tool_name = ""
    tool_args: dict[str, Any] = {}

    if settings.llm_enabled:
        prompt = (
            "Classify the user request. Return JSON only with keys intent, tool_name, tool_args. "
            "intent must be one of knowledge, repo, issue, direct. "
            "Use knowledge for document or policy questions, repo for code search, issue for issue lookup, "
            "and direct for general conversation. tool_args must be an object.\n\n"
            f"User request: {question}"
        )
        try:
            plan = _parse_json(await llm.chat([{"role": "user", "content": prompt}], json_mode=True))
            intent = str(plan.get("intent", "direct"))
            tool_name = str(plan.get("tool_name", ""))
            tool_args = dict(plan.get("tool_args") or {})
        except (LLMError, ValueError, TypeError, json.JSONDecodeError):
            pass

    if intent not in {"knowledge", "repo", "issue", "direct"}:
        intent = "direct"

    if not settings.llm_enabled:
        lowered = question.lower()
        if any(word in question for word in ("文档", "知识库", "规范", "怎么做", "说明")):
            intent = "knowledge"
        elif any(word in lowered for word in ("repo", "code", "代码", "函数", "类", "搜索")):
            intent = "repo"
        elif any(word in question for word in ("工单", "issue", "缺陷", "问题")):
            intent = "issue"

    if intent == "repo":
        tool_name = tool_name or "search_repo"
        tool_args = tool_args or {"query": question, "max_results": 10}
    elif intent == "issue":
        tool_name = tool_name or "get_issue"
        tool_args = tool_args or {"issue_id": question.split()[-1]}

    return {
        "intent": intent,
        "tool_name": tool_name,
        "tool_args": tool_args,
        "steps": _add_step(state, f"route:{intent}"),
    }


@observe("agent.retrieve")
async def retrieve_node(state: AgentState) -> AgentState:
    client = MCPClient(settings.dev_mcp_url)
    try:
        result = await client.call_tool(
            "search_knowledge",
            {"query": state["question"], "max_results": 5},
        )
        evidence = [result]
        return {
            "evidence": evidence,
            "steps": _add_step(state, "knowledge:sqlite-fts5"),
        }
    except MCPError as exc:
        return {
            "evidence": [{"text": f"Local knowledge unavailable: {exc}"}],
            "steps": _add_step(state, "knowledge:unavailable"),
            "degraded": True,
        }


@observe("agent.tool")
async def tool_node(state: AgentState) -> AgentState:
    client = MCPClient(settings.dev_mcp_url)
    try:
        result = await client.call_tool(state["tool_name"], state.get("tool_args", {}))
        return {
            "evidence": [result],
            "steps": _add_step(state, f"mcp:{state['tool_name']}"),
        }
    except MCPError as exc:
        return {
            "evidence": [{"text": f"Tool unavailable: {exc}"}],
            "steps": _add_step(state, f"mcp:{state['tool_name']}:failed"),
            "degraded": True,
        }


@observe("agent.answer")
async def answer_node(state: AgentState) -> AgentState:
    evidence = state.get("evidence", [])
    evidence_text = json.dumps(evidence, ensure_ascii=False, default=str)[:12000]
    citations = []
    for item in evidence:
        structured = item.get("structured_content") if isinstance(item, dict) else None
        if isinstance(structured, dict):
            source = structured.get("source") or structured.get("url") or structured.get("file")
            if source:
                citations.append(str(source))
            for result in structured.get("results", []):
                if isinstance(result, dict) and result.get("source"):
                    citations.append(str(result["source"]))

    if settings.llm_enabled:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a careful engineering assistant. Answer in Chinese. Use the supplied evidence. "
                    "If evidence is insufficient, say so explicitly. Do not invent citations or claim a tool ran "
                    "when it did not. Keep the answer structured and practical."
                ),
            },
            {
                "role": "user",
                "content": f"Question:\n{state['question']}\n\nEvidence:\n{evidence_text}",
            },
        ]
        try:
            answer = await llm.chat(messages)
        except LLMError as exc:
            answer = f"模型暂不可用：{exc}\n\n可用证据：\n{evidence_text}"
            state = {**state, "degraded": True}
    else:
        answer = (
            "当前未配置 OPENAI_API_KEY，已完成路由和工具调用，但未生成模型回答。\n\n"
            f"可用证据：\n{evidence_text}"
        )

    return {
        "answer": answer,
        "citations": list(dict.fromkeys(citations)),
        "steps": _add_step(state, "answer"),
    }


def route_after_classification(state: AgentState) -> str:
    intent = state.get("intent", "direct")
    if intent == "knowledge":
        return "retrieve"
    if intent in {"repo", "issue"}:
        return "tool"
    return "answer"


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("route", route_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("tool", tool_node)
    builder.add_node("answer", answer_node)
    builder.add_edge(START, "route")
    builder.add_conditional_edges(
        "route",
        route_after_classification,
        {"retrieve": "retrieve", "tool": "tool", "answer": "answer"},
    )
    builder.add_edge("retrieve", "answer")
    builder.add_edge("tool", "answer")
    builder.add_edge("answer", END)
    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()


@observe("agent.run")
async def run_agent(question: str, thread_id: str) -> AgentState:
    return await graph.ainvoke(
        {"question": question, "thread_id": thread_id, "steps": [], "degraded": False},
        config={"configurable": {"thread_id": thread_id}},
    )
