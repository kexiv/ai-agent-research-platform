"""Run a small DeepEval regression set against the local graph.

This is intentionally a script rather than a pytest suite: it is also used as a
portfolio demo to show how Agent and RAG quality are measured.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.graph import run_agent


async def collect() -> list[dict[str, str]]:
    rows = []
    for line in (Path(__file__).parent / "dataset.jsonl").read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        result = await run_agent(item["question"], f"eval-{item['id']}")
        rows.append({**item, "actual": result.get("answer", "")})
    return rows


def main() -> None:
    try:
        from deepeval import evaluate
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
        from deepeval.test_case import LLMTestCase
    except ImportError as exc:
        raise SystemExit("Install project dependencies before running evals: pip install -e .") from exc

    rows = asyncio.run(collect())
    test_cases = [
        LLMTestCase(
            input=row["question"],
            actual_output=row["actual"],
            retrieval_context=[row["expected"]],
        )
        for row in rows
    ]
    evaluate(
        test_cases,
        metrics=[AnswerRelevancyMetric(threshold=0.5), FaithfulnessMetric(threshold=0.5)],
    )


if __name__ == "__main__":
    main()
