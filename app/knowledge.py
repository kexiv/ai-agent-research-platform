from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable

from app.config import get_settings


SUPPORTED_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".sql",
}
IGNORED_DIRS = {".git", ".venv", "__pycache__", "infra", "node_modules"}
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
HAN_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
WORD_RE = re.compile(r"[A-Za-z0-9_./:-]+|[\u4e00-\u9fff]+")


class KnowledgeStore:
    """Small local knowledge store backed by SQLite FTS5.

    The index is deliberately rebuildable: source documents remain plain files under
    ``data/knowledge`` and the SQLite database is only a generated search artifact.
    """

    def __init__(self, root: str | Path | None = None, db_path: str | Path | None = None):
        settings = get_settings()
        self.root = Path(root or settings.knowledge_root).resolve()
        self.db_path = Path(db_path or settings.knowledge_db_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    content TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
                USING fts5(content, source UNINDEXED);
                """
            )

    def _iter_files(self) -> Iterable[Path]:
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            if any(part in IGNORED_DIRS for part in path.relative_to(self.root).parts):
                continue
            yield path

    @staticmethod
    def _fts_text(text: str) -> str:
        """Add spaced Chinese bigrams so FTS5 can retrieve Chinese queries."""
        bigrams: list[str] = []
        for match in HAN_RUN_RE.finditer(text):
            value = match.group(0)
            bigrams.extend(value[index : index + 2] for index in range(len(value) - 1))
            if len(value) == 1:
                bigrams.append(value)
        return f"{text}\n{' '.join(bigrams)}" if bigrams else text

    @staticmethod
    def _query_tokens(query: str) -> list[str]:
        tokens: list[str] = []
        for match in WORD_RE.finditer(query):
            value = match.group(0)
            if HAN_RUN_RE.fullmatch(value):
                if len(value) == 1:
                    tokens.append(value)
                else:
                    tokens.extend(value[index : index + 2] for index in range(len(value) - 1))
            else:
                tokens.append(value.lower())
        return list(dict.fromkeys(token for token in tokens if token.strip()))

    @staticmethod
    def _match_expression(tokens: list[str]) -> str:
        return " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)

    @staticmethod
    def _chunks(text: str) -> Iterable[tuple[int, int, str]]:
        if not text:
            return
        start = 0
        chunk_index = 0
        step = CHUNK_SIZE - CHUNK_OVERLAP
        while start < len(text):
            end = min(len(text), start + CHUNK_SIZE)
            yield chunk_index, start, text[start:end]
            if end == len(text):
                break
            start += step
            chunk_index += 1

    def ingest(self) -> dict[str, object]:
        files = list(self._iter_files())
        document_count = 0
        chunk_count = 0

        with self._connect() as connection:
            connection.execute("DELETE FROM chunks_fts")
            connection.execute("DELETE FROM chunks")
            connection.execute("DELETE FROM documents")

            for path in files:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                source = path.relative_to(self.root).as_posix()
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                connection.execute(
                    "INSERT INTO documents(id, source, sha256, updated_at) "
                    "VALUES (?, ?, ?, datetime('now'))",
                    (source, source, digest),
                )
                document_count += 1

                for chunk_index, start_offset, content in self._chunks(text):
                    cursor = connection.execute(
                        "INSERT INTO chunks(document_id, source, chunk_index, start_line, end_line, content) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            source,
                            source,
                            chunk_index,
                            text.count("\n", 0, start_offset) + 1,
                            text.count("\n", 0, start_offset + len(content)) + 1,
                            content,
                        ),
                    )
                    connection.execute(
                        "INSERT INTO chunks_fts(rowid, content, source) VALUES (?, ?, ?)",
                        (cursor.lastrowid, self._fts_text(content), source),
                    )
                    chunk_count += 1

            connection.commit()

        return {
            "documents": document_count,
            "chunks": chunk_count,
            "root": str(self.root),
            "db_path": str(self.db_path),
        }

    def search(self, query: str, max_results: int = 5) -> list[dict[str, object]]:
        tokens = self._query_tokens(query)
        if not tokens:
            return []

        limit = max(1, min(int(max_results), 20))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT c.source, c.start_line, c.end_line, c.content, bm25(chunks_fts) AS rank
                FROM chunks_fts
                JOIN chunks AS c ON c.id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (self._match_expression(tokens), limit),
            ).fetchall()

        return [
            {
                "source": row["source"],
                "start_line": row["start_line"],
                "end_line": row["end_line"],
                "content": row["content"],
                "score": round(max(0.0, -float(row["rank"])), 6),
            }
            for row in rows
        ]


def main() -> None:
    print(json.dumps(KnowledgeStore().ingest(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
