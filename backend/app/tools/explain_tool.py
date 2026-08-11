from app.config import settings
from app.gemini_client import generate_text
from app.analysis.anomaly import detect_anomalies

async def explain_data(query: str, data: list[dict], context: str = "") -> dict:
    """Tool entrypoint. Invokes Gemini to explain/summarize the data returned
    by execute_query in plain, natural language, incorporating statistical anomalies.
    """
    # Expose and run statistical anomaly detection
    columns = list(data[0].keys()) if data else []
    anomalies = []
    try:
        anomalies = detect_anomalies(columns, data)
    except Exception:
        pass

    # Restrict data size passed to prompt to avoid context limit issues
    truncated_data = data[:100]
    prompt = (
        f"You are a Senior Data Analyst. Explain the insights from the following SQL query results in plain English.\n\n"
        f"SQL Query: {query}\n"
        f"Query Results (JSON format, up to first 100 rows):\n{truncated_data}\n\n"
    )
    if anomalies:
        anomalies_text = "\n".join(f"- {a['description']}" for a in anomalies)
        prompt += f"Detected Statistical Anomalies:\n{anomalies_text}\n\n"

    if context:
        prompt += f"User's analytical context/focus: {context}\n\n"
        
    prompt += "Provide a natural language summary listing key metrics, trends, and business insights. Specifically mention any detected anomalies and their potential impact. Keep the tone professional, helpful, and concise."

    try:
        explanation = await generate_text(prompt)
        if not explanation:
            explanation = "Could not generate explanation for the data."
        return {
            "success": True,
            "explanation": explanation,
            "anomalies": anomalies
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "error_type": "explanation_failed",
            "message": str(exc)
        }

EXPLAIN_DATA_TOOL_DECLARATION = {
    "name": "explain_data",
    "description": (
        "Generate natural language insights, key metrics, and summaries from query data returned by execute_query."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The SQL query that produced the data."},
            "data": {
                "type": "array",
                "items": {"type": "object"},
                "description": "The rows array returned by execute_query."
            },
            "context": {
                "type": "string",
                "description": "Optional details about what specific insights or metrics the user is asking about."
            }
        },
        "required": ["query", "data"],
    },
}
