from app.config import settings
from google import genai

async def explain_data(query: str, data: list[dict], context: str = "") -> dict:
    """Tool entrypoint. Invokes Gemini to explain/summarize the data returned
    by execute_query in plain, natural language.
    """
    client = genai.Client(api_key=settings.gemini_api_key)
    
    # Restrict data size passed to prompt to avoid context limit issues
    truncated_data = data[:100]
    prompt = (
        f"You are a Senior Data Analyst. Explain the insights from the following SQL query results in plain English.\n\n"
        f"SQL Query: {query}\n"
        f"Query Results (JSON format, up to first 100 rows):\n{truncated_data}\n\n"
    )
    if context:
        prompt += f"User's analytical context/focus: {context}\n\n"
        
    prompt += "Provide a natural language summary listing key metrics, trends, and business insights. Keep the tone professional, helpful, and concise."

    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        explanation = response.text or "Could not generate explanation for the data."
        return {
            "success": True,
            "explanation": explanation
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
