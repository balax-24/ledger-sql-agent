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


@app.get("/api/starter-questions")
async def starter_questions():
    try:
        from app.tools.schema_tool import get_schema_data
        data = await get_schema_data()
        tables = data.get("tables", [])
        
        questions = []
        table_names = {t["name"].lower() for t in tables}
        
        # 1. Look for sales/orders/revenue/amount related queries
        financial_table = None
        revenue_col = None
        for t in tables:
            tname = t["name"].lower()
            if any(k in tname for k in ["sale", "order", "invoice", "payment", "revenue", "transaction"]):
                financial_table = t["name"]
                for col in t["columns"]:
                    cname = col["name"].lower()
                    if any(k in cname for k in ["amount", "revenue", "total", "price", "subtotal", "sum"]):
                        revenue_col = col["name"]
                        break
                if financial_table:
                    break

        if financial_table and revenue_col:
            questions.append(f"What is the total revenue in the {financial_table} table?")
            questions.append(f"Show the monthly trend of {revenue_col} from the {financial_table} table.")
        elif financial_table:
            questions.append(f"How many entries are in the {financial_table} table?")
            questions.append(f"Show me the latest 5 transactions/orders from the {financial_table} table.")

        # 2. Look for customer/user/client related tables
        customer_table = None
        name_col = None
        for t in tables:
            tname = t["name"].lower()
            if any(k in tname for k in ["customer", "user", "client", "member"]):
                customer_table = t["name"]
                for col in t["columns"]:
                    cname = col["name"].lower()
                    if any(k in cname for k in ["name", "email", "username", "first_name"]):
                        name_col = col["name"]
                        break
                if customer_table:
                    break

        if customer_table:
            if name_col:
                questions.append(f"Who are the top customers/users listed in the {customer_table} table?")
            else:
                questions.append(f"List the first 10 records from the {customer_table} table.")

        # 3. Look for product/item/inventory related tables
        product_table = None
        for t in tables:
            tname = t["name"].lower()
            if any(k in tname for k in ["product", "item", "inventory", "stock", "catalog"]):
                product_table = t["name"]
                break
        
        if product_table:
            questions.append(f"What are the most popular products in the {product_table} table?")

        # Fallbacks to ensure we always have 4 high-quality starter questions
        all_table_names = [t["name"] for t in tables]
        if len(questions) < 4 and all_table_names:
            # Add general queries
            for tname in all_table_names:
                q1 = f"Show me a breakdown of the {tname} table."
                if q1 not in questions and len(questions) < 4:
                    questions.append(q1)
                q2 = f"How many rows are in the {tname} table?"
                if q2 not in questions and len(questions) < 4:
                    questions.append(q2)

        # Hardcoded default questions if database is completely empty or schema check failed
        if not questions:
            questions = [
                "What tables are in my database?",
                "Show me the total sales by product category.",
                "Who are our top 5 customers by order count?",
                "Which products are currently low on stock?"
            ]

        return {"questions": questions[:4]}
    except Exception:
        # Graceful fallback
        return {
            "questions": [
                "What tables are in my database?",
                "Show me the total sales by product category.",
                "Who are our top 5 customers by order count?",
                "Which products are currently low on stock?"
            ]
        }


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
