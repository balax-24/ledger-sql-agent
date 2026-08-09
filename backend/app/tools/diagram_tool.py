import re

from app.tools.schema_tool import get_schema_data

_SAFE_ID = re.compile(r"[^A-Za-z0-9_]")


def _mermaid_id(name: str) -> str:
    return _SAFE_ID.sub("_", name).upper()


def _mermaid_label(text: str) -> str:
    return text.replace('"', "'")


async def generate_er_diagram(tables: list[str] | None = None) -> dict:
    """Tool entrypoint. Builds Mermaid erDiagram syntax from the same
    introspection get_schema uses, so the diagram can never disagree with
    what get_schema told the model a moment earlier.
    """
    try:
        schema = await get_schema_data()
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error_type": "introspection_failed", "message": str(exc)}

    all_tables = schema["tables"]
    if tables:
        wanted = {t.lower() for t in tables}
        all_tables = [t for t in all_tables if t["name"].lower() in wanted]
        if not all_tables:
            return {
                "success": False,
                "error_type": "no_matching_tables",
                "message": f"None of {tables} matched a table in the database.",
            }

    lines = ["erDiagram"]
    for table in all_tables:
        lines.append(f"  {_mermaid_id(table['name'])} {{")
        for col in table["columns"]:
            pg_type = re.sub(r"[^a-zA-Z0-9]", "_", col["type"])
            lines.append(f"    {pg_type} {col['name']}")
        lines.append("  }")

    seen_edges = set()
    for table in all_tables:
        for fk in table["foreign_keys"]:
            to_table = fk["references"].split(".")[0]
            if to_table.lower() not in {t["name"].lower() for t in all_tables}:
                continue
            edge = (_mermaid_id(to_table), _mermaid_id(table["name"]))
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            lines.append(f'  {edge[0]} ||--o{{ {edge[1]} : "has"')

    return {"success": True, "mermaid": "\n".join(lines)}


async def generate_flowchart(title: str, steps: list[dict]) -> dict:
    """Tool entrypoint. `steps` is a list of {id, label, next[]} — the model
    builds this itself, typically by reading a status/enum column via
    get_schema and turning its values into ordered steps.
    """
    if not steps:
        return {"success": False, "error_type": "empty_steps", "message": "Provide at least one step."}

    ids = {s["id"] for s in steps}
    lines = ["flowchart LR"]
    for step in steps:
        node_id = _mermaid_id(step["id"])
        label = _mermaid_label(step["label"])
        lines.append(f'  {node_id}["{label}"]')

    for step in steps:
        for nxt in step.get("next", []):
            if nxt not in ids:
                continue
            lines.append(f"  {_mermaid_id(step['id'])} --> {_mermaid_id(nxt)}")

    return {"success": True, "title": title, "mermaid": "\n".join(lines)}


ER_DIAGRAM_TOOL_DECLARATION = {
    "name": "generate_er_diagram",
    "description": (
        "Introspect the database and produce a Mermaid entity-relationship "
        "diagram of tables and their foreign key relationships."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "tables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional subset of table names to include. Omit to include all tables.",
            }
        },
        "required": [],
    },
}

FLOWCHART_TOOL_DECLARATION = {
    "name": "generate_flowchart",
    "description": (
        "Produce a Mermaid flowchart describing a process, such as how orders "
        "move through the system. Infer the steps from schema structure "
        "(e.g. a status column's possible values) or from a natural-language "
        "description the user gave."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "next": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of steps that follow this one",
                        },
                    },
                    "required": ["id", "label"],
                },
            },
        },
        "required": ["title", "steps"],
    },
}
