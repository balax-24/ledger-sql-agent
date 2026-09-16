import asyncio
import time
import uuid

from app.config import settings
from app.gemini_client import (
    build_history,
    function_response_content,
    generate_turn,
    model_turn_content,
)
from app.logger import logger, set_request_id
from app.tools.registry import TOOL_DECLARATIONS, TOOL_FUNCTIONS, VISUAL_TOOLS


async def run_agent(messages: list[dict], request_id: str | None = None):
    """Async generator yielding SSE-ready {"event": ..., "data": ...} dicts
    for one user turn. `messages` is the full conversation history.
    """
    req_id = request_id or f"req_{uuid.uuid4().hex[:8]}"
    set_request_id(req_id)

    last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    logger.info("Agent run started for prompt: '%s'", last_user_msg[:80])

    contents = build_history(messages)

    for iteration in range(1, settings.max_tool_iterations + 1):
        if iteration > 1:
            await asyncio.sleep(0.5)
        logger.info("Agent turn %d/%d invoking model", iteration, settings.max_tool_iterations)
        try:
            response = await generate_turn(contents, TOOL_DECLARATIONS)
        except Exception as exc:  # noqa: BLE001
            logger.error("Model turn failed: %s", exc)
            yield {
                "event": "error",
                "data": {"message": f"AI service encountered an issue: {exc}"},
            }
            yield {"event": "done", "data": None}
            return

        function_calls = getattr(response, "function_calls", None) or []

        if not function_calls:
            text = getattr(response, "text", None) or "I don't have a response for that — could you rephrase?"
            logger.info("Model returned final text response (%d chars)", len(text))
            async for chunk in _pseudo_stream(text):
                yield {"event": "token", "data": chunk}
            yield {"event": "done", "data": None}
            return

        contents.append(model_turn_content(response))

        for call in function_calls:
            name = call.name
            if not name:
                continue
            args = dict(call.args or {})

            logger.info("Executing tool: %s", name)
            yield {"event": "tool_call", "data": {"name": name, "args": args}}

            tool_fn = TOOL_FUNCTIONS.get(name)
            t_start = time.perf_counter()
            if tool_fn is None:
                result = {
                    "success": False,
                    "error_type": "unknown_tool",
                    "message": f"No tool named '{name}'.",
                }
            else:
                try:
                    result = await tool_fn(**args)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Tool '%s' crashed: %s", name, exc, exc_info=True)
                    result = {"success": False, "error_type": "tool_crashed", "message": str(exc)}

            duration_ms = (time.perf_counter() - t_start) * 1000
            logger.info("Tool '%s' completed in %.1fms (success=%s)", name, duration_ms, result.get("success"))

            visible = name in VISUAL_TOOLS and bool(result.get("success"))
            yield {
                "event": "tool_result",
                "data": {"name": name, "result": result, "visible": visible},
            }

            contents.append(function_response_content(name, result))

    logger.warning("Agent reached maximum tool iterations (%d)", settings.max_tool_iterations)
    yield {
        "event": "error",
        "data": {
            "message": "The analysis could not be completed within the allowed tool steps. Please try breaking your question into smaller parts."
        },
    }
    yield {"event": "done", "data": None}


async def _pseudo_stream(text: str, words_per_chunk: int = 3, delay: float = 0.02):
    """Chunks a complete response into small pieces to show progressive typing."""
    words = text.split(" ")
    for i in range(0, len(words), words_per_chunk):
        is_last = i + words_per_chunk >= len(words)
        yield " ".join(words[i : i + words_per_chunk]) + ("" if is_last else " ")
        await asyncio.sleep(delay)
