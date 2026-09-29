from __future__ import annotations

import os
from pathlib import Path

from app.config import get_settings
from app.knowledge import KnowledgeStore

try:
    from mcp.server import MCPServer
except ImportError as exc:  # pragma: no cover - exercised when dependencies are absent
    MCPServer = None  # type: ignore[assignment]
    _MCP_IMPORT_ERROR = exc
else:
    _MCP_IMPORT_ERROR = None


if MCPServer is not None:
    mcp = MCPServer("research-agent-dev-tools")

    @mcp.tool()
    def search_repo(query: str, max_results: int = 10) -> dict[str, object]:
        """Search source and documentation files under REPO_ROOT."""
        root = Path(get_settings().repo_root).resolve()
        allowed = {".py", ".md", ".ts", ".tsx", ".js", ".go", ".java", ".rs"}
        matches: list[dict[str, object]] = []
        query_lower = query.lower()
        for path in root.rglob("*"):
            if len(matches) >= max_results or not path.is_file() or path.suffix not in allowed:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            hit_lines = [
                {"line": index, "text": line[:300]}
                for index, line in enumerate(lines, start=1)
                if query_lower in line.lower()
            ]
            if hit_lines:
                matches.append({"file": str(path.relative_to(root)), "matches": hit_lines[:5]})
        return {"query": query, "results": matches}

    @mcp.tool()
    def search_knowledge(query: str, max_results: int = 5) -> dict[str, object]:
        """Search local Markdown and text documents with SQLite FTS5."""
        store = KnowledgeStore()
        return {
            "backend": "sqlite-fts5",
            "query": query,
            "results": store.search(query, max_results=max_results),
        }

    @mcp.tool()
    def ingest_knowledge() -> dict[str, object]:
        """Rebuild the local SQLite FTS5 index from KNOWLEDGE_ROOT."""
        store = KnowledgeStore()
        return {"backend": "sqlite-fts5", **store.ingest()}

    @mcp.tool()
    def get_issue(issue_id: str) -> dict[str, object]:
        """Return a deterministic local issue fixture for Agent tool-call demos."""
        fixtures = {
            "AI-101": {
                "id": "AI-101",
                "title": "RAG citation disappears in streaming response",
                "status": "open",
                "labels": ["rag", "streaming"],
                "description": "Citations are present in the final object but missing from SSE chunks.",
            },
            "AI-102": {
                "id": "AI-102",
                "title": "MCP tool timeout is not surfaced to the user",
                "status": "in_progress",
                "labels": ["mcp", "reliability"],
                "description": "The Agent retries indefinitely when a remote tool does not respond.",
            },
        }
        return fixtures.get(issue_id.upper(), {"id": issue_id, "status": "not_found"})


def main() -> None:
    if MCPServer is None:
        raise RuntimeError("MCP SDK is unavailable") from _MCP_IMPORT_ERROR
    port = int(os.getenv("DEV_MCP_PORT", "8001"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
