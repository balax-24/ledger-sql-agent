from app.db import get_pool

_COLUMNS_QUERY = """
select table_name, column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
order by table_name, ordinal_position;
"""

_FOREIGN_KEYS_QUERY = """
select
  tc.table_name as from_table,
  kcu.column_name as from_column,
  ccu.table_name as to_table,
  ccu.column_name as to_column
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu
  on tc.constraint_name = kcu.constraint_name and tc.table_schema = kcu.table_schema
join information_schema.constraint_column_usage ccu
  on tc.constraint_name = ccu.constraint_name and tc.table_schema = ccu.table_schema
where tc.constraint_type = 'FOREIGN KEY' and tc.table_schema = 'public';
"""


async def get_schema_data() -> dict:
    """Shared introspection used by both the get_schema tool and the ER
    diagram tool, so the two never drift out of sync with each other."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        columns = await conn.fetch(_COLUMNS_QUERY)
        fks = await conn.fetch(_FOREIGN_KEYS_QUERY)

    tables: dict[str, dict] = {}
    for row in columns:
        table = tables.setdefault(row["table_name"], {"name": row["table_name"], "columns": [], "foreign_keys": []})
        table["columns"].append(
            {
                "name": row["column_name"],
                "type": row["data_type"],
                "nullable": row["is_nullable"] == "YES",
            }
        )
    for row in fks:
        if row["from_table"] in tables:
            tables[row["from_table"]]["foreign_keys"].append(
                {"column": row["from_column"], "references": f"{row['to_table']}.{row['to_column']}"}
            )

    return {"tables": list(tables.values())}


async def get_schema() -> dict:
    """Tool entrypoint: return every table's columns and foreign keys."""
    try:
        data = await get_schema_data()
        return {"success": True, **data}
    except Exception as exc:  # noqa: BLE001 - surfaced to the LLM, not swallowed
        return {"success": False, "error_type": "introspection_failed", "message": str(exc)}


SCHEMA_TOOL_DECLARATION = {
    "name": "get_schema",
    "description": (
        "Return every table's columns (name, type, nullable) and foreign key "
        "relationships in the connected database. Call this first whenever you "
        "don't already know the schema — never guess table or column names."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}
