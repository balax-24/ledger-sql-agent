"""
Gemini GenAI SDK integration with provider abstraction.
agent.py interacts with the configured LLMProvider (RealGeminiProvider or MockGeminiProvider).
"""
import asyncio
import os
import re
from typing import Any
from google import genai
from google.genai import types, models, _common  # type: ignore

from app.config import settings
from app.logger import logger

# --- MONKEY PATCHES TO PRESERVE & RE-INJECT THOUGHT SIGNATURES ---
orig_Part_from_mldev = models._Part_from_mldev  # type: ignore
orig_Part_from_vertex = models._Part_from_vertex  # type: ignore
orig_Part_to_mldev = models._Part_to_mldev  # type: ignore
orig_Part_to_vertex = models._Part_to_vertex  # type: ignore
orig_from_response = _common.BaseModel._from_response  # type: ignore


def patched_Part_from_mldev(api_client, from_object, parent_object=None):
    res = orig_Part_from_mldev(api_client, from_object, parent_object)  # type: ignore
    sig = None
    if isinstance(from_object, dict):
        sig = from_object.get("thoughtSignature") or from_object.get("thought_signature")
    elif hasattr(from_object, "thoughtSignature"):
        sig = getattr(from_object, "thoughtSignature")
    elif hasattr(from_object, "thought_signature"):
        sig = getattr(from_object, "thought_signature")

    if sig:
        res["_thought_signature"] = sig
    return res


def patched_Part_from_vertex(api_client, from_object, parent_object=None):
    res = orig_Part_from_vertex(api_client, from_object, parent_object)  # type: ignore
    sig = None
    if isinstance(from_object, dict):
        sig = from_object.get("thoughtSignature") or from_object.get("thought_signature")
    elif hasattr(from_object, "thoughtSignature"):
        sig = getattr(from_object, "thoughtSignature")
    elif hasattr(from_object, "thought_signature"):
        sig = getattr(from_object, "thought_signature")

    if sig:
        res["_thought_signature"] = sig
    return res


models._Part_from_mldev = patched_Part_from_mldev  # type: ignore
models._Part_from_vertex = patched_Part_from_vertex  # type: ignore


def patched_from_response(cls, response, kwargs):
    signatures = []

    def extract_signatures(data, path=[]):
        if isinstance(data, dict):
            if "_thought_signature" in data:
                signatures.append((list(path), data.pop("_thought_signature")))
            for k, v in data.items():
                extract_signatures(v, path + [k])
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                extract_signatures(item, path + [idx])

    extract_signatures(response)

    validated = orig_from_response.__func__(cls, response, kwargs)  # type: ignore

    for path, sig in signatures:
        obj = validated
        for step in path:
            if isinstance(obj, list):
                obj = obj[step]
            else:
                from pydantic.alias_generators import to_snake

                snake_step = to_snake(step)
                if hasattr(obj, snake_step):
                    obj = getattr(obj, snake_step)
                elif hasattr(obj, step):
                    obj = getattr(obj, step)
                else:
                    obj = None
                    break
        if obj is not None:
            object.__setattr__(obj, "thought_signature", sig)

    return validated


_common.BaseModel._from_response = classmethod(patched_from_response)  # type: ignore


def patched_Part_to_mldev(api_client, from_object, parent_object=None):
    res = orig_Part_to_mldev(api_client, from_object, parent_object)  # type: ignore
    sig = None
    if hasattr(from_object, "thought_signature"):
        sig = getattr(from_object, "thought_signature")
    elif isinstance(from_object, dict):
        sig = from_object.get("thought_signature") or from_object.get("thoughtSignature")

    if sig:
        res["thoughtSignature"] = sig
    return res


def patched_Part_to_vertex(api_client, from_object, parent_object=None):
    res = orig_Part_to_vertex(api_client, from_object, parent_object)  # type: ignore
    sig = None
    if hasattr(from_object, "thought_signature"):
        sig = getattr(from_object, "thought_signature")
    elif isinstance(from_object, dict):
        sig = from_object.get("thought_signature") or from_object.get("thoughtSignature")

    if sig:
        res["thoughtSignature"] = sig
    return res


models._Part_to_mldev = patched_Part_to_mldev  # type: ignore
models._Part_to_vertex = patched_Part_to_vertex  # type: ignore
# --- END MONKEY PATCHES ---


SYSTEM_INSTRUCTION = """You are a data analyst assistant embedded in a chat app. \
You have tools to inspect a Postgres database, run read-only SQL, explain query results in natural language, and render \
charts and diagrams in the chat UI.

Rules:
- Never guess a table or column name. Call get_schema first if you're not sure.
- Only execute_query can touch the database, and it only accepts SELECT statements.
- After execute_query returns rows suited to visualization, call generate_chart \
  with the SAME rows rather than re-describing them. Pick bar for category \
  comparisons, line for trends over time, pie for proportions, scatter for \
  correlation between two numeric columns.
- Call explain_data on query results from execute_query when the user wants an explanation, summary, or report of the query results.
- For "draw the ER diagram" style requests, call generate_er_diagram.
- For "how does X flow" or "decision tree" or tree-structured logic requests, infer steps and branch conditions from the schema/logic, and call generate_flowchart.
- If a tool returns success: false, read the message and either fix the call \
  and retry once, or explain the problem to the user in plain language — \
  never repeat the exact same failing call twice.
- After showing a chart or diagram, give a short, concrete insight about \
  what it shows. Keep prose tight; the visual is doing most of the work.
"""


def _build_tools(declarations: list[dict]) -> list[types.Tool]:
    function_declarations = [
        types.FunctionDeclaration(
            name=d["name"],
            description=d["description"],
            parameters=d["parameters"],
        )
        for d in declarations
    ]
    return [types.Tool(function_declarations=function_declarations)]


def build_history(messages: list[dict]) -> list[types.Content]:
    """messages: [{"role": "user"|"assistant", "content": str}, ...]"""
    history = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        history.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
    return history


def model_turn_content(response) -> types.Content:
    """The model's own turn (may contain a function_call part), to be
    appended to history verbatim before the tool result."""
    return response.candidates[0].content


def function_response_content(name: str, response_data: dict) -> types.Content:
    part = types.Part.from_function_response(name=name, response=response_data)
    return types.Content(role="user", parts=[part])


class LLMProvider:
    """Base interface for LLM operations to allow swapping real and mock providers."""

    async def generate_turn(self, contents: list[types.Content], tool_declarations: list[dict]):
        raise NotImplementedError

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        raise NotImplementedError

    async def is_available(self) -> bool:
        raise NotImplementedError


class RealGeminiProvider(LLMProvider):
    def __init__(self):
        self._client: genai.Client | None = None
        self._last_checked: float = 0.0
        self._cached_available: bool = False

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not configured.")
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    async def generate_turn(self, contents: list[types.Content], tool_declarations: list[dict]):
        client = self._get_client()
        config = types.GenerateContentConfig(
            tools=_build_tools(tool_declarations),  # type: ignore
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
        )
        max_attempts = 4
        for attempt in range(max_attempts):
            try:
                return await client.aio.models.generate_content(
                    model=settings.gemini_model,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                error_str = str(exc)
                is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                is_unavailable = "503" in error_str or "UNAVAILABLE" in error_str
                if (is_rate_limit or is_unavailable) and attempt < max_attempts - 1:
                    import re
                    match = re.search(r"retry(?:\s+in|\s+after)?\s+([0-9\.]+)\s*s", error_str, re.IGNORECASE)
                    if not match:
                        match = re.search(r'retryDelay["\']?\s*:\s*["\']?([0-9\.]+)s?', error_str, re.IGNORECASE)
                    if match:
                        backoff = float(match.group(1)) + 1.0
                    else:
                        backoff = (attempt + 1) * 5.0
                    logger.warning("Gemini API rate limit/capacity hit. Retrying in %.1fs (attempt %d/%d)...", backoff, attempt + 1, max_attempts)
                    await asyncio.sleep(backoff)
                    continue
                if is_unavailable:
                    raise RuntimeError("The AI model service is temporarily at high capacity. Please retry.") from exc
                if is_rate_limit:
                    raise RuntimeError("AI API rate limit exceeded. Please wait a moment and try again.") from exc
                raise

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        client = self._get_client()
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            )
        max_attempts = 4
        for attempt in range(max_attempts):
            try:
                response = await client.aio.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config=config,
                )
                return response.text or ""
            except Exception as exc:
                error_str = str(exc)
                is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                is_unavailable = "503" in error_str or "UNAVAILABLE" in error_str
                if (is_rate_limit or is_unavailable) and attempt < max_attempts - 1:
                    import re
                    match = re.search(r"retry(?:\s+in|\s+after)?\s+([0-9\.]+)\s*s", error_str, re.IGNORECASE)
                    if not match:
                        match = re.search(r'retryDelay["\']?\s*:\s*["\']?([0-9\.]+)s?', error_str, re.IGNORECASE)
                    if match:
                        backoff = float(match.group(1)) + 1.0
                    else:
                        backoff = (attempt + 1) * 5.0
                    logger.warning("Gemini API rate limit/capacity hit in text generation. Retrying in %.1fs (attempt %d/%d)...", backoff, attempt + 1, max_attempts)
                    await asyncio.sleep(backoff)
                    continue
                logger.warning("generate_text failed with model %s: %s", settings.gemini_model, exc)
                if is_unavailable:
                    raise RuntimeError("The AI model service is temporarily at high capacity. Please retry.") from exc
                if is_rate_limit:
                    raise RuntimeError("AI API rate limit exceeded. Please wait a moment and try again.") from exc
                raise

    async def is_available(self) -> bool:
        if not settings.gemini_api_key:
            return False
        import time
        now = time.time()
        if (now - self._last_checked) < 60.0:
            return self._cached_available
        try:
            client = self._get_client()
            # Fast ping with 1 token
            resp = await client.aio.models.generate_content(
                model=settings.gemini_model,
                contents="ping",
            )
            self._cached_available = bool(resp)
            self._last_checked = now
            return self._cached_available
        except Exception:
            self._cached_available = False
            self._last_checked = now
            return False


class MockFunctionCall:
    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args


class MockCandidate:
    def __init__(self, content):
        self.content = content


class MockResponse:
    def __init__(self, text: str | None = None, function_calls: list[MockFunctionCall] | None = None):
        self.text = text
        self.function_calls = function_calls or []
        parts = []
        if text:
            parts.append(types.Part.from_text(text=text))
        if function_calls:
            for fc in function_calls:
                parts.append(types.Part.from_function_call(name=fc.name, args=fc.args))
        content = types.Content(role="model", parts=parts)
        self.candidates = [MockCandidate(content)]


class MockGeminiProvider(LLMProvider):
    """Deterministic mock provider for end-to-end testing and CI without calling external APIs."""

    def __init__(self, turn_responses: list[MockResponse] | None = None, text_response: str = "Mock explanation"):
        self.turn_responses = list(turn_responses or [])
        self.text_response = text_response
        self.call_count = 0

    async def generate_turn(self, contents: list[types.Content], tool_declarations: list[dict]):
        if self.turn_responses:
            return self.turn_responses.pop(0)
        return MockResponse(text="Mock default answer")

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        return self.text_response

    async def is_available(self) -> bool:
        return True


# Global provider instance
_provider: LLMProvider = RealGeminiProvider()


def get_provider() -> LLMProvider:
    return _provider


def set_provider(provider: LLMProvider):
    global _provider
    _provider = provider


# Convenience top-level functions used by agent.py and tools
async def generate_turn(contents: list[types.Content], tool_declarations: list[dict]):
    return await _provider.generate_turn(contents, tool_declarations)


async def generate_text(prompt: str, system_instruction: str | None = None) -> str:
    return await _provider.generate_text(prompt, system_instruction)


async def is_model_available() -> bool:
    return await _provider.is_available()
