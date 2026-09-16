import json
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.agent import run_agent
from app.config import settings
from app.db import close_pool, get_pool
from app.gemini_client import is_model_available
from app.logger import logger, set_request_id
from app.tools.schema_tool import get_schema

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Ledger backend server...")
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        logger.info("Database connection pool established successfully.")
    except Exception as exc:
        logger.warning("Database connection could not be established at startup: %s", exc)
    yield
    logger.info("Closing Ledger backend resources...")
    await close_pool()

app = FastAPI(title="Ledger DB Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:8]}"
    set_request_id(req_id)
    response = await call_next(request)
    response.headers["x-request-id"] = req_id
    return response


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@app.get("/api/health")
async def health():
    db_status = "disconnected"
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "connected"
    except Exception as exc:
        logger.warning("Health check: DB connection check failed: %s", exc)
        db_status = "disconnected"

    model_status = "unconfigured"
    if settings.gemini_api_key:
        try:
            available = await is_model_available()
            model_status = "available" if available else "degraded"
        except Exception:
            model_status = "degraded"

    overall_status = "healthy" if (db_status == "connected" and model_status == "available") else "degraded"

    return {
        "status": overall_status,
        "database": db_status,
        "model": model_status,
        "model_name": settings.gemini_model,
        "row_limit": settings.query_row_limit,
    }


@app.get("/api/schema")
async def api_schema():
    return await get_schema()


@app.get("/api/starter-questions")
async def starter_questions():
    """Returns curated starter prompts based on dynamic schema introspection."""
    try:
        from app.tools.schema_tool import get_schema_data
        data = await get_schema_data()
        tables = data.get("tables", [])
        table_names = {t["name"].lower() for t in tables}

        questions = [
            "Show me the top 5 customers by revenue",
            "Show monthly revenue trends for the last 12 months",
            "Find unusual changes in monthly sales",
            "Draw me the ER diagram for this database",
        ]

        if "products" in table_names:
            questions.append("Which products generate the highest profit margins?")
        if "orders" in table_names:
            questions.append("What is the distribution of order statuses?")

        return {"questions": questions[:5]}
    except Exception as exc:
        logger.warning("Starter questions fallback triggered: %s", exc)
        return {
            "questions": [
                "Show me the top 5 customers by revenue",
                "Show monthly revenue trends for the last 12 months",
                "Find unusual changes in monthly sales",
                "Draw me the ER diagram for this database",
                "Which products generate the highest profit margins?",
            ]
        }


def _sse_format(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.messages:
        return JSONResponse(status_code=400, content={"message": "No messages provided."})

    messages = [m.model_dump() for m in req.messages]
    req_id = f"req_{uuid.uuid4().hex[:8]}"

    async def event_stream():
        async for evt in run_agent(messages, request_id=req_id):
            yield _sse_format(evt["event"], evt["data"])

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "x-request-id": req_id,
        },
    )
