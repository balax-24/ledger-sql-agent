import json
import pytest
from unittest.mock import patch, AsyncMock

from app.agent import run_agent
from app.gemini_client import (
    MockFunctionCall,
    MockGeminiProvider,
    MockResponse,
    get_provider,
    set_provider,
)
from app.main import ChatRequest, Message, api_schema, chat, health, starter_questions


@pytest.mark.asyncio
async def test_api_health_endpoint():
    with patch("app.main.is_model_available", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = True
        res = await health()
        assert "status" in res
        assert "database" in res
        assert "model" in res
        assert "row_limit" in res
        assert res["row_limit"] == 100


@pytest.mark.asyncio
@patch("app.main.get_pool")
async def test_api_health_degraded_when_db_down(mock_get_pool):
    mock_get_pool.side_effect = Exception("DB connection timeout")
    with patch("app.main.is_model_available", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = True
        res = await health()
        assert res["status"] == "degraded"
        assert res["database"] == "disconnected"


@pytest.mark.asyncio
async def test_api_starter_questions():
    res = await starter_questions()
    assert "questions" in res
    assert len(res["questions"]) >= 4
    # Check that top questions are present
    assert any("customers" in q.lower() for q in res["questions"])


@pytest.mark.asyncio
async def test_api_schema():
    res = await api_schema()
    assert res["success"] is True
    assert "tables" in res
    table_names = {t["name"] for t in res["tables"]}
    assert {"customers", "products", "orders", "order_items"}.issubset(table_names)


@pytest.mark.asyncio
async def test_end_to_end_agent_flow_with_mock_provider():
    """End-to-end integration test (Phase 23):
    user question -> agent -> tool calls (get_schema, execute_query, generate_chart) -> model answer.
    Runs completely offline using MockGeminiProvider.
    """
    turn1_resp = MockResponse(
        function_calls=[MockFunctionCall("get_schema", {})]
    )

    turn2_resp = MockResponse(
        function_calls=[
            MockFunctionCall(
                "execute_query",
                {
                    "sql": "SELECT name, price FROM products ORDER BY price DESC LIMIT 5",
                    "reasoning": "Find top products by price",
                },
            )
        ]
    )

    turn3_resp = MockResponse(
        function_calls=[
            MockFunctionCall(
                "generate_chart",
                {
                    "chart_type": "bar",
                    "title": "Top Products by Price",
                    "x_field": "name",
                    "y_field": "price",
                    "data": [
                        {"name": "Quantum Monitor", "price": 499.99},
                        {"name": "Espresso Machine", "price": 299.99},
                    ],
                },
            )
        ]
    )

    turn4_resp = MockResponse(
        text="The highest priced product is Quantum Monitor at $499.99, followed by Espresso Machine at $299.99."
    )

    mock_provider = MockGeminiProvider(
        turn_responses=[turn1_resp, turn2_resp, turn3_resp, turn4_resp]
    )
    original_provider = get_provider()
    set_provider(mock_provider)

    try:
        messages = [{"role": "user", "content": "What are our most expensive products?"}]
        events = []
        async for evt in run_agent(messages):
            events.append(evt)

        event_types = [e["event"] for e in events]
        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert "token" in event_types
        assert "done" in event_types

        # Verify tool calls happened in expected order
        tool_calls = [e["data"]["name"] for e in events if e["event"] == "tool_call"]
        assert tool_calls == ["get_schema", "execute_query", "generate_chart"]

        # Verify chart card was marked visible
        chart_result = next(
            e["data"] for e in events if e["event"] == "tool_result" and e["data"]["name"] == "generate_chart"
        )
        assert chart_result["visible"] is True
        assert chart_result["result"]["spec"]["chart_type"] == "bar"

        # Verify tokens streamed
        tokens = [e["data"] for e in events if e["event"] == "token"]
        full_text = "".join(tokens)
        assert "Quantum Monitor" in full_text
        assert "$499.99" in full_text

    finally:
        set_provider(original_provider)
