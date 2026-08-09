VALID_CHART_TYPES = {"bar", "line", "pie", "scatter"}


async def generate_chart(chart_type: str, title: str, x_field: str, y_field: str, data: list[dict]) -> dict:
    """Tool entrypoint. Deliberately does no rendering here — it validates
    the spec and hands it through as structured data. The frontend (Recharts)
    owns rendering. Keeps the backend a pure data/orchestration layer and the
    chart-drawing logic in exactly one place.
    """
    if chart_type not in VALID_CHART_TYPES:
        return {
            "success": False,
            "error_type": "invalid_chart_type",
            "message": f"chart_type must be one of {sorted(VALID_CHART_TYPES)}, got '{chart_type}'.",
        }
    if not data:
        return {"success": False, "error_type": "empty_data", "message": "No rows to chart. Run a query first."}

    missing_x = [i for i, row in enumerate(data) if x_field not in row]
    missing_y = [i for i, row in enumerate(data) if y_field not in row]
    if missing_x or missing_y:
        return {
            "success": False,
            "error_type": "missing_field",
            "message": (
                f"x_field '{x_field}' or y_field '{y_field}' is missing from some rows. "
                f"Available columns: {sorted(data[0].keys())}"
            ),
        }

    return {
        "success": True,
        "spec": {
            "chart_type": chart_type,
            "title": title,
            "x_field": x_field,
            "y_field": y_field,
            "data": data[:200],  # keep the payload sane even if the model passes a big result set
        },
    }


CHART_TOOL_DECLARATION = {
    "name": "generate_chart",
    "description": (
        "Render a chart in the chat UI from tabular data already retrieved via "
        "execute_query. Pick the chart type that fits the data: bar for "
        "categorical comparisons, line for trends over time, pie for "
        "proportional breakdowns, scatter for correlation between two numeric fields."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "chart_type": {"type": "string", "enum": sorted(VALID_CHART_TYPES)},
            "title": {"type": "string"},
            "x_field": {"type": "string", "description": "Column to use as x-axis / category / label"},
            "y_field": {"type": "string", "description": "Column to use as y-axis / value"},
            "data": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Row objects, typically the `rows` array returned by execute_query",
            },
        },
        "required": ["chart_type", "title", "x_field", "y_field", "data"],
    },
}
