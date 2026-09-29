from fastapi import FastAPI

from app.config import get_settings
from app.graph import run_agent
from app.models import ChatRequest, ChatResponse

app = FastAPI(title="Research Agent", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "llm_enabled": settings.llm_enabled,
        "langfuse_enabled": settings.langfuse_enabled,
        "knowledge_root": settings.knowledge_root,
        "knowledge_db_path": settings.knowledge_db_path,
        "dev_mcp_url": settings.dev_mcp_url,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    result = await run_agent(request.question, request.thread_id)
    return ChatResponse(
        answer=result.get("answer", ""),
        citations=result.get("citations", []),
        steps=result.get("steps", []),
        degraded=bool(result.get("degraded", False)),
        thread_id=request.thread_id,
    )


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
