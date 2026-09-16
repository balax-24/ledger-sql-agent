import pytest
from sqlglot import expressions as exp
from app.tools.query_tool import _validate_select_only, UnsafeQueryError


def test_valid_select():
    sql = "SELECT id, name FROM customers WHERE active = true ORDER BY name LIMIT 10"
    stmt = _validate_select_only(sql)
    assert isinstance(stmt, exp.Select)


def test_valid_select_with_join_and_group_by():
    sql = """
    SELECT c.name, COUNT(o.id) as order_count, SUM(oi.quantity * oi.unit_price) as revenue
    FROM customers c
    JOIN orders o ON c.id = o.customer_id
    JOIN order_items oi ON o.id = oi.order_id
    GROUP BY c.name
    HAVING COUNT(o.id) > 2
    ORDER BY revenue DESC
    """
    stmt = _validate_select_only(sql)
    assert isinstance(stmt, exp.Select)


def test_valid_select_with_cte():
    sql = """
    WITH monthly_sales AS (
        SELECT date_trunc('month', order_date) as month, SUM(quantity * unit_price) as total
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        GROUP BY 1
    )
    SELECT month, total FROM monthly_sales ORDER BY month
    """
    stmt = _validate_select_only(sql)
    assert isinstance(stmt, exp.Select)


def test_valid_select_with_union():
    sql = """
    SELECT id, name FROM customers WHERE region = 'North'
    UNION ALL
    SELECT id, name FROM customers WHERE region = 'South'
    """
    stmt = _validate_select_only(sql)
    assert isinstance(stmt, (exp.Select, exp.Union))


def test_valid_select_with_subquery():
    sql = """
    SELECT name, price FROM products
    WHERE id IN (SELECT product_id FROM order_items WHERE quantity > 2)
    """
    stmt = _validate_select_only(sql)
    assert isinstance(stmt, exp.Select)


def test_valid_select_with_comments():
    sql = """
    -- This is a comment mentioning DROP and DELETE
    SELECT id, name /* inline comment */ FROM customers
    """
    stmt = _validate_select_only(sql)
    assert isinstance(stmt, exp.Select)


# --- SECURITY REJECTION TESTS ---

def test_reject_delete():
    with pytest.raises(UnsafeQueryError, match="Only SELECT statements are allowed"):
        _validate_select_only("DELETE FROM customers WHERE id = 1")


def test_reject_update():
    with pytest.raises(UnsafeQueryError, match="Only SELECT statements are allowed"):
        _validate_select_only("UPDATE customers SET name = 'Hacked' WHERE id = 1")


def test_reject_insert():
    with pytest.raises(UnsafeQueryError, match="Only SELECT statements are allowed"):
        _validate_select_only("INSERT INTO customers (name, email, region) VALUES ('x', 'x@x.com', 'North')")


def test_reject_drop():
    with pytest.raises(UnsafeQueryError, match="Only SELECT statements are allowed"):
        _validate_select_only("DROP TABLE customers CASCADE")


def test_reject_create():
    with pytest.raises(UnsafeQueryError, match="Only SELECT statements are allowed"):
        _validate_select_only("CREATE TABLE backdoor (id serial)")


def test_reject_alter():
    with pytest.raises(UnsafeQueryError, match="Only SELECT statements are allowed"):
        _validate_select_only("ALTER TABLE customers ADD COLUMN hacked TEXT")


def test_reject_truncate():
    with pytest.raises(UnsafeQueryError, match="Only SELECT statements are allowed"):
        _validate_select_only("TRUNCATE TABLE customers")


def test_reject_multiple_statements():
    with pytest.raises(UnsafeQueryError, match="Only a single SQL statement is allowed"):
        _validate_select_only("SELECT id FROM customers; DROP TABLE customers;")


def test_reject_locking_for_update():
    with pytest.raises(UnsafeQueryError, match="Row locking clauses"):
        _validate_select_only("SELECT id FROM customers FOR UPDATE")


def test_reject_locking_for_share():
    with pytest.raises(UnsafeQueryError, match="Row locking clauses"):
        _validate_select_only("SELECT id FROM customers FOR SHARE")


def test_reject_dangerous_function_pg_sleep():
    with pytest.raises(UnsafeQueryError, match="Function 'pg_sleep' is forbidden"):
        _validate_select_only("SELECT pg_sleep(10)")


def test_reject_dangerous_function_pg_terminate():
    with pytest.raises(UnsafeQueryError, match="Function 'pg_terminate_backend' is forbidden"):
        _validate_select_only("SELECT pg_terminate_backend(12345)")


def test_reject_dangerous_function_dblink():
    with pytest.raises(UnsafeQueryError, match="Function 'dblink' is forbidden"):
        _validate_select_only("SELECT * FROM dblink('host=attacker.com', 'SELECT 1') AS t(x int)")


def test_reject_write_in_cte():
    # PostgreSQL supports data-modifying CTEs: WITH d AS (DELETE ...) SELECT ...
    sql = "WITH d AS (DELETE FROM customers WHERE id = 1 RETURNING *) SELECT * FROM d"
    with pytest.raises(UnsafeQueryError, match="Query contains disallowed write/DDL operation"):
        _validate_select_only(sql)


def test_reject_empty_query():
    with pytest.raises(UnsafeQueryError, match="Query cannot be empty"):
        _validate_select_only("   ")


def test_reject_invalid_syntax():
    with pytest.raises(UnsafeQueryError, match="Could not parse SQL"):
        _validate_select_only("SELECT FROM WHERE 1 = = 2")
