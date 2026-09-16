import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncpg
from app.tools.query_tool import execute_query


@pytest.mark.asyncio
@patch("app.tools.query_tool.get_pool")
@patch("app.tools.query_tool._attempt_self_correction")
async def test_self_correction_success_on_syntax_error(mock_self_correct, mock_get_pool):
    """Verifies that a typographical/syntax error can be corrected and safely executed."""
    mock_conn = AsyncMock()
    mock_row = MagicMock()
    mock_row.keys.return_value = ["id", "name"]
    mock_row.__getitem__.side_effect = lambda k: {"id": 1, "name": "Apex"}[k]
    mock_row.items.return_value = [("id", 1), ("name", "Apex")]

    # First fetch raises syntax error, second returns rows
    mock_conn.fetch.side_effect = [
        asyncpg.exceptions.PostgresSyntaxError("syntax error near WHERE"),
        [mock_row],
    ]
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)
    mock_get_pool.return_value = mock_pool

    mock_self_correct.return_value = "SELECT id, name FROM customers"

    res = await execute_query("SELECT id, name FROM customers WHERE", reasoning="Find customers")

    assert res["success"] is True
    assert res["self_corrected"] is True
    assert res["sql_executed"].startswith("SELECT id, name FROM customers")
    assert res["rows"][0]["name"] == "Apex"


@pytest.mark.asyncio
@patch("app.tools.query_tool.get_pool")
@patch("app.tools.query_tool._attempt_self_correction")
async def test_self_correction_malicious_query_blocked(mock_self_correct, mock_get_pool):
    """CRITICAL SECURITY TEST (Phase 5):
    If a query fails and the LLM correction produces a destructive query (e.g. DELETE),
    the security validator MUST intercept and block it, ensuring it is NEVER executed.
    """
    mock_conn = AsyncMock()
    mock_conn.fetch.side_effect = asyncpg.exceptions.UndefinedTableError('relation "wrong_table" does not exist')

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)
    mock_get_pool.return_value = mock_pool

    # Attacker tries to inject a DELETE statement via LLM self-correction
    mock_self_correct.return_value = "DELETE FROM customers"

    res = await execute_query("SELECT * FROM wrong_table", reasoning="Test attack")

    # Verify that the malicious query was BLOCKED
    assert res["success"] is False
    assert res["error_type"] == "unsafe_query"
    assert "blocked" in res["message"].lower() or "only select" in res["message"].lower()

    # Verify that mock_conn.fetch was called ONLY once (for initial query), NEVER for DELETE!
    assert mock_conn.fetch.call_count == 1
    call_args = mock_conn.fetch.call_args_list[0][0][0]
    assert "DELETE" not in call_args


@pytest.mark.asyncio
@patch("app.tools.query_tool.get_pool")
@patch("app.tools.query_tool._attempt_self_correction")
async def test_self_correction_drop_table_blocked(mock_self_correct, mock_get_pool):
    """CRITICAL SECURITY TEST:
    If a query fails and the LLM correction produces DROP TABLE customers,
    the security validator MUST intercept and block it, ensuring it is NEVER executed.
    """
    mock_conn = AsyncMock()
    mock_conn.fetch.side_effect = asyncpg.exceptions.UndefinedTableError('relation "wrong_table" does not exist')

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)
    mock_get_pool.return_value = mock_pool

    mock_self_correct.return_value = "DROP TABLE customers;"

    res = await execute_query("SELECT * FROM wrong_table", reasoning="Test drop attack")

    # Verify that the malicious DROP TABLE was BLOCKED
    assert res["success"] is False
    assert res["error_type"] == "unsafe_query"
    assert "blocked" in res["message"].lower() or "disallowed" in res["message"].lower() or "only select" in res["message"].lower()

    # Verify that mock_conn.fetch was called ONLY once (for initial query), NEVER for DROP!
    assert mock_conn.fetch.call_count == 1
    call_args = mock_conn.fetch.call_args_list[0][0][0]
    assert "DROP" not in call_args



@pytest.mark.asyncio
@patch("app.tools.query_tool.get_pool")
@patch("app.tools.query_tool._attempt_self_correction")
async def test_self_correction_locking_clause_blocked(mock_self_correct, mock_get_pool):
    """Verifies that self-correction cannot inject row-locking clauses."""
    mock_conn = AsyncMock()
    mock_conn.fetch.side_effect = asyncpg.exceptions.UndefinedTableError('relation "t" does not exist')

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)
    mock_get_pool.return_value = mock_pool

    mock_self_correct.return_value = "SELECT id FROM customers FOR UPDATE"

    res = await execute_query("SELECT id FROM t")
    assert res["success"] is False
    assert res["error_type"] == "unsafe_query"
    assert "locking" in res["message"].lower()


@pytest.mark.asyncio
@patch("app.tools.query_tool.get_pool")
@patch("app.tools.query_tool._attempt_self_correction")
async def test_self_correction_failure_handles_gracefully(mock_self_correct, mock_get_pool):
    """Verifies that if self-correction cannot resolve the issue, a clean sanitized error is returned."""
    mock_conn = AsyncMock()
    mock_conn.fetch.side_effect = asyncpg.exceptions.UndefinedTableError('relation "nonexistent" does not exist')

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)
    mock_get_pool.return_value = mock_pool

    mock_self_correct.return_value = None  # Correction couldn't find a fix

    res = await execute_query("SELECT * FROM nonexistent")
    assert res["success"] is False
    assert res["error_type"] == "query_failed"
    assert "requested table does not exist" in res["message"]
