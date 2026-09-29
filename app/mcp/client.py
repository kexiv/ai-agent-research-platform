from __future__ import annotations

import asyncio
from typing import Any, Iterable

from app.config import get_settings


class MCPError(RuntimeError):
    """Raised when an MCP server cannot be reached or a tool fails."""


def _tool_name(tool: Any) -> str:
    return str(getattr(tool, "name", ""))


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    text = getattr(content, "text", None)
    if text is not None:
        return str(text)
    if isinstance(content, dict):
        return str(content.get("text") or content)
    return str(content)


def normalize_result(result: Any) -> dict[str, Any]:
    """Convert an MCP CallToolResult into JSON-friendly evidence."""

    structured = getattr(result, "structured_content", None)
    content = getattr(result, "content", None)
    texts = [_content_to_text(item) for item in content or []]
    return {
        "structured_content": structured,
        "text": "\n".join(texts),
        "is_error": bool(getattr(result, "is_error", False)),
    }


class MCPClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.timeout = get_settings().mcp_request_timeout_seconds

    async def _client(self):
        try:
            from mcp import Client
        except ImportError as exc:
            raise MCPError("Install the MCP Python SDK with: pip install 'mcp>=2'") from exc
        return Client(self.url)

    async def list_tools(self) -> list[str]:
        client = await self._client()
        try:
            async with asyncio.timeout(self.timeout):
                async with client as session:
                    result = await session.list_tools()
                    return [_tool_name(tool) for tool in getattr(result, "tools", [])]
        except Exception as exc:
            raise MCPError(f"MCP list_tools failed for {self.url}: {exc}") from exc

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        client = await self._client()
        try:
            async with asyncio.timeout(self.timeout):
                async with client as session:
                    result = await session.call_tool(name, arguments)
                    normalized = normalize_result(result)
                    if normalized["is_error"]:
                        raise MCPError(normalized["text"] or f"MCP tool failed: {name}")
                    return normalized
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError(f"MCP call failed for {self.url}/{name}: {exc}") from exc

    async def call_first_matching(
        self,
        candidates: Iterable[str],
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        tools = await self.list_tools()
        lowered = {name.lower(): name for name in tools}
        for candidate in candidates:
            if candidate.lower() in lowered:
                return await self.call_tool(lowered[candidate.lower()], arguments)
        for candidate in candidates:
            for name in tools:
                if candidate.lower() in name.lower():
                    return await self.call_tool(name, arguments)
        raise MCPError(f"No matching MCP tool. Available tools: {tools}")
