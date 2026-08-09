import asyncio

from app.config import settings
from app.gemini_client import build_history, function_response_content, generate_turn, model_turn_content
from app.tools.registry import TOOL_DECLARATIONS, TOOL_FUNCTIONS, VISUAL_TOOLS


async def run_agent(messages: list[dict]):
    """Async generator yielding SSE-ready {"event": ..., "data": ...} dicts
    for one user turn. `messages` is the full conversation so far — the
    frontend is stateless-free and just resends everything each request.
    """
    contents = build_history(messages)

    for _ in range(settings.max_tool_iterations):
        try:
            response = await generate_turn(contents, TOOL_DECLARATIONS)
        except Exception as exc:  # noqa: BLE001
            yield {"event": "error", "data": {"message": f"Model call failed: {exc}"}}
            yield {"event": "done", "data": None}
            return

        function_calls = response.function_calls or []

        if not function_calls:
            text = response.text or "I don't have a response for that — could you rephrase?"
            async for chunk in _pseudo_stream(text):
                yield {"event": "token", "data": chunk}
            yield {"event": "done", "data": None}
            return

        contents.append(model_turn_content(response))

        # Gemini can request several tool calls in one turn; run them in
        # order so a later call can build on an earlier result in the same turn.
        for call in function_calls:
            name = call.name
            if not name:
                continue
            args = dict(call.args or {})

            yield {"event": "tool_call", "data": {"name": name, "args": args}}

            tool_fn = TOOL_FUNCTIONS.get(name)
            if tool_fn is None:
                result = {"success": False, "error_type": "unknown_tool", "message": f"No tool named '{name}'."}
            else:
                try:
                    result = await tool_fn(**args)
                except Exception as exc:  # noqa: BLE001
                    result = {"success": False, "error_type": "tool_crashed", "message": str(exc)}

            visible = name in VISUAL_TOOLS and bool(result.get("success"))
            yield {"event": "tool_result", "data": {"name": name, "result": result, "visible": visible}}

            contents.append(function_response_content(name, result))

    yield {
        "event": "error",
        "data": {"message": f"Stopped after {settings.max_tool_iterations} tool calls without a final answer."},
    }
    yield {"event": "done", "data": None}


async def _pseudo_stream(text: str, words_per_chunk: int = 3, delay: float = 0.02):
    """Chunks a complete response into small pieces so the chat UI can show
    it appearing progressively. See the note in gemini_client.py for why
    this isn't native token streaming."""
    words = text.split(" ")
    for i in range(0, len(words), words_per_chunk):
        is_last = i + words_per_chunk >= len(words)
        yield " ".join(words[i : i + words_per_chunk]) + ("" if is_last else " ")
        await asyncio.sleep(delay)
