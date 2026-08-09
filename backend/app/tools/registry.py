"""
The tool registry is the extensibility point of this whole architecture.
Adding a 6th tool (e.g. the bonus decision-tree diagram) means adding one
function + one declaration here — nothing in agent.py or main.py changes.
"""
from app.tools.chart_tool import CHART_TOOL_DECLARATION, generate_chart
from app.tools.diagram_tool import (
    ER_DIAGRAM_TOOL_DECLARATION,
    FLOWCHART_TOOL_DECLARATION,
    generate_er_diagram,
    generate_flowchart,
)
from app.tools.explain_tool import EXPLAIN_DATA_TOOL_DECLARATION, explain_data
from app.tools.query_tool import (
    EXECUTE_QUERY_TOOL_DECLARATION,
    execute_query,
    run_sql_query,
)
from app.tools.schema_tool import SCHEMA_TOOL_DECLARATION, get_schema

TOOL_FUNCTIONS = {
    "get_schema": get_schema,
    "execute_query": execute_query,
    "run_sql_query": run_sql_query,  # kept for robust model fallback
    "explain_data": explain_data,
    "generate_chart": generate_chart,
    "generate_er_diagram": generate_er_diagram,
    "generate_flowchart": generate_flowchart,
}

TOOL_DECLARATIONS = [
    SCHEMA_TOOL_DECLARATION,
    EXECUTE_QUERY_TOOL_DECLARATION,
    EXPLAIN_DATA_TOOL_DECLARATION,
    CHART_TOOL_DECLARATION,
    ER_DIAGRAM_TOOL_DECLARATION,
    FLOWCHART_TOOL_DECLARATION,
]

# Tools whose successful result should be rendered as its own card in the
# chat UI rather than just fed back into the model silently.
VISUAL_TOOLS = {"generate_chart", "generate_er_diagram", "generate_flowchart", "explain_data"}


