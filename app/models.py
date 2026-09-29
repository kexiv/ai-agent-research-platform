from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    thread_id: str = Field(default="default", min_length=1, max_length=128)


class ChatResponse(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    degraded: bool = False
    thread_id: str


class AgentState(TypedDict, total=False):
    question: str
    thread_id: str
    intent: Literal["knowledge", "repo", "issue", "direct"]
    tool_name: str
    tool_args: dict[str, Any]
    evidence: list[dict[str, Any]]
    citations: list[str]
    answer: str
    steps: list[str]
    degraded: bool
