import time
from app.db import get_pool
from app.logger import logger

_COLUMNS_QUERY = """
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable
FROM information_schema.columns c
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;
"""

_PRIMARY_KEYS_QUERY = """
SELECT
    conrelid::regclass::text AS table_name,
    a.attname AS column_name
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE c.contype = 'p' AND n.nspname = 'public';
"""

_FOREIGN_KEYS_QUERY = """
SELECT
    conrelid::regclass::text AS from_table,
    a.attname AS from_column,
    confrelid::regclass::text AS to_table,
    af.attname AS to_column
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
JOIN pg_attribute af ON af.attrelid = c.confrelid AND af.attnum = ANY(c.confkey)
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE c.contype = 'f' AND n.nspname = 'public';
"""

# In-memory cache for schema introspection
_schema_cache: dict | None = None
_schema_cache_time: float = 0
SCHEMA_CACHE_TTL_SECONDS = 60.0


def invalidate_schema_cache():
    """Clear schema cache, e.g. after migrations or tests."""
    global _schema_cache, _schema_cache_time
    _schema_cache = None
    _schema_cache_time = 0


async def get_schema_data(use_cache: bool = True) -> dict:
    """Shared introspection used by get_schema, ER diagrams, and starter questions.
    Returns tables, columns, primary keys, and foreign keys.
    """
    global _schema_cache, _schema_cache_time
    now = time.time()
    if use_cache and _schema_cache is not None and (now - _schema_cache_time) < SCHEMA_CACHE_TTL_SECONDS:
        return _schema_cache

    pool = await get_pool()
    async with pool.acquire() as conn:
        columns = await conn.fetch(_COLUMNS_QUERY)
        pks = await conn.fetch(_PRIMARY_KEYS_QUERY)
        fks = await conn.fetch(_FOREIGN_KEYS_QUERY)

    # Set of (table_name, column_name) that are primary keys
    pk_set = {(row["table_name"], row["column_name"]) for row in pks}

    tables: dict[str, dict] = {}
    for row in columns:
        tbl_name = row["table_name"]
        col_name = row["column_name"]
        table = tables.setdefault(
            tbl_name,
            {
                "name": tbl_name,
                "columns": [],
                "primary_keys": [],
                "foreign_keys": [],
            },
        )
        is_pk = (tbl_name, col_name) in pk_set
        if is_pk and col_name not in table["primary_keys"]:
            table["primary_keys"].append(col_name)

        table["columns"].append(
            {
                "name": col_name,
                "type": row["data_type"],
                "nullable": row["is_nullable"] == "YES",
                "primary_key": is_pk,
            }
        )

    for row in fks:
        from_tbl = row["from_table"]
        if from_tbl in tables:
            tables[from_tbl]["foreign_keys"].append(
                {
                    "column": row["from_column"],
                    "references": f"{row['to_table']}.{row['to_column']}",
                }
            )

    result = {"tables": list(tables.values())}
    _schema_cache = result
    _schema_cache_time = now
    logger.info("Introspected schema: discovered %d tables", len(result["tables"]))
    return result


async def get_schema() -> dict:
    """Tool entrypoint: return every table's columns and foreign keys."""
    try:
        data = await get_schema_data()
        return {"success": True, **data}
    except Exception as exc:  # noqa: BLE001
        logger.error("Schema introspection failed: %s", exc)
        return {"success": False, "error_type": "introspection_failed", "message": str(exc)}


SCHEMA_TOOL_DECLARATION = {
    "name": "get_schema",
    "description": (
        "Return every table's columns (name, type, nullable, primary_key) and foreign key "
        "relationships in the connected database. Call this first whenever you "
        "don't already know the schema — never guess table or column names."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}
