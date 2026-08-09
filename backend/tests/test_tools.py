import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sqlglot
from sqlglot import expressions as exp

from app.tools.query_tool import (
    _validate_select_only,
    _apply_row_limit,
    execute_query,
    UnsafeQueryError,
)
from app.tools.chart_tool import generate_chart
from app.tools.diagram_tool import generate_er_diagram, generate_flowchart
from app.tools.explain_tool import explain_data
from app.tools.schema_tool import get_schema


# --- 1. QUERY TOOL TESTS ---

def test_validate_select_only_valid():
    sql = "SELECT id, name FROM customers WHERE active = true"
    stmt = _validate_select_only(sql)
    assert isinstance(stmt, exp.Select)


def test_validate_select_only_invalid_delete():
    sql = "DELETE FROM customers WHERE id = 1"
    with pytest.raises(UnsafeQueryError) as exc_info:
        _validate_select_only(sql)
    assert "Only SELECT statements are allowed" in str(exc_info.value)


def test_validate_select_only_invalid_multiple():
    sql = "SELECT id FROM customers; DROP TABLE customers;"
    with pytest.raises(UnsafeQueryError) as exc_info:
        _validate_select_only(sql)
    assert "Only a single SQL statement is allowed" in str(exc_info.value)


def test_validate_select_only_invalid_syntax():
    sql = "SELECT FROM WHERE"
    with pytest.raises(UnsafeQueryError) as exc_info:
        _validate_select_only(sql)
    assert "Could not parse SQL" in str(exc_info.value)


def test_apply_row_limit():
    # Case 1: No limit exists
    stmt = _validate_select_only("SELECT id FROM customers")
    limited = _apply_row_limit(stmt, 100)
    assert "LIMIT 100" in limited

    # Case 2: Exists but smaller limit
    stmt = _validate_select_only("SELECT id FROM customers LIMIT 50")
    limited = _apply_row_limit(stmt, 100)
    assert "LIMIT 50" in limited

    # Case 3: Exists but larger limit
    stmt = _validate_select_only("SELECT id FROM customers LIMIT 500")
    limited = _apply_row_limit(stmt, 100)
    assert "LIMIT 100" in limited


@pytest.mark.asyncio
@patch("app.tools.query_tool.get_pool")
async def test_execute_query_success(mock_get_pool):
    # Setup mock connection and rows
    mock_conn = AsyncMock()
    mock_row = MagicMock()
    mock_row.keys.return_value = ["id", "name"]
    mock_row.__getitem__.side_effect = lambda k: {"id": 1, "name": "Alice"}[k]
    mock_row.items.return_value = [("id", 1), ("name", "Alice")]
    
    # We must mock fetch as a coroutine
    mock_conn.fetch = AsyncMock(return_value=[mock_row])
    
    # Mock acquire context manager correctly
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)
    
    # get_pool is an async function, so mock_get_pool must be an AsyncMock returning mock_pool
    mock_get_pool.return_value = mock_pool

    res = await execute_query("SELECT id, name FROM customers", reasoning="Get all customers")
    assert res["success"] is True
    assert res["row_count"] == 1
    assert res["columns"] == ["id", "name"]
    assert res["rows"][0]["name"] == "Alice"


# --- 2. CHART TOOL TESTS ---

@pytest.mark.asyncio
async def test_generate_chart_success():
    data = [{"month": "Jan", "sales": 100}, {"month": "Feb", "sales": 150}]
    res = await generate_chart(
        chart_type="line",
        title="Monthly Sales",
        x_field="month",
        y_field="sales",
        data=data,
    )
    assert res["success"] is True
    assert res["spec"]["chart_type"] == "line"
    assert res["spec"]["x_field"] == "month"
    assert len(res["spec"]["data"]) == 2


@pytest.mark.asyncio
async def test_generate_chart_invalid_type():
    data = [{"month": "Jan", "sales": 100}]
    res = await generate_chart(
        chart_type="invalid_type",
        title="Title",
        x_field="month",
        y_field="sales",
        data=data,
    )
    assert res["success"] is False
    assert res["error_type"] == "invalid_chart_type"


@pytest.mark.asyncio
async def test_generate_chart_missing_field():
    data = [{"month": "Jan"}]  # missing "sales" (y_field)
    res = await generate_chart(
        chart_type="bar",
        title="Title",
        x_field="month",
        y_field="sales",
        data=data,
    )
    assert res["success"] is False
    assert res["error_type"] == "missing_field"


# --- 3. DIAGRAM TOOL TESTS ---

@pytest.mark.asyncio
@patch("app.tools.diagram_tool.get_schema_data")
async def test_generate_er_diagram(mock_get_schema_data):
    mock_get_schema_data.return_value = {
        "tables": [
            {
                "name": "customers",
                "columns": [{"name": "id", "type": "integer"}],
                "foreign_keys": [],
            }
        ]
    }
    res = await generate_er_diagram(tables=["customers"])
    assert res["success"] is True
    assert "erDiagram" in res["mermaid"]
    assert "CUSTOMERS" in res["mermaid"]


@pytest.mark.asyncio
async def test_generate_flowchart():
    steps = [
        {"id": "cart", "label": "Shopping Cart", "next": ["checkout"]},
        {"id": "checkout", "label": "Checkout", "next": []},
    ]
    res = await generate_flowchart(title="Order Flow", steps=steps)
    assert res["success"] is True
    assert "flowchart LR" in res["mermaid"]
    assert "CART" in res["mermaid"]
    assert "CHECKOUT" in res["mermaid"]


# --- 4. EXPLAIN DATA TOOL TESTS ---

@pytest.mark.asyncio
@patch("app.tools.explain_tool.genai.Client")
async def test_explain_data_success(mock_genai_client):
    # Setup mock Client response
    mock_response = MagicMock()
    mock_response.text = "This query shows our highest paying customer is Alice."
    
    mock_aio_models = AsyncMock()
    mock_aio_models.generate_content.return_value = mock_response
    
    mock_client_instance = MagicMock()
    mock_client_instance.aio.models = mock_aio_models
    mock_genai_client.return_value = mock_client_instance

    res = await explain_data(
        query="SELECT name FROM customers",
        data=[{"name": "Alice"}],
        context="Who is the highest paying customer?",
    )
    assert res["success"] is True
    assert "Alice" in res["explanation"]


# --- 5. SCHEMA TOOL TESTS ---

@pytest.mark.asyncio
@patch("app.tools.schema_tool.get_schema_data")
async def test_get_schema(mock_get_schema_data):
    mock_get_schema_data.return_value = {
        "tables": [
            {
                "name": "products",
                "columns": [{"name": "id", "type": "integer"}],
                "foreign_keys": [],
            }
        ]
    }
    res = await get_schema()
    assert res["success"] is True
    assert len(res["tables"]) == 1
    assert res["tables"][0]["name"] == "products"
