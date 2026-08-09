import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent import run_agent
from app.config import settings
from app.db import close_pool, get_pool

app = FastAPI(title="LLM DB Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@app.on_event("startup")
async def startup():
    await get_pool()  # fail fast on a bad DATABASE_URL instead of on the first chat request


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


from app.tools.schema_tool import get_schema


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": settings.gemini_model}


@app.get("/api/schema")
async def api_schema():
    return await get_schema()


def _sse_format(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]

    async def event_stream():
        async for evt in run_agent(messages):
            yield _sse_format(evt["event"], evt["data"])

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
