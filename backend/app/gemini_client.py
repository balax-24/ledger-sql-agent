"""
All Google GenAI SDK specifics live in this one file. agent.py never touches
`google.genai` types directly — it only sees plain dicts. That's what makes
swapping providers (Claude, OpenAI) later a one-file change: write a
claude_client.py with the same four function signatures and swap the import
in agent.py.

Uses the manual (non-automatic) function-calling flow so the agent loop in
agent.py can emit its own SSE events between tool calls, and control which
tool results get shown to the user as chart/diagram cards vs stay internal.

Note on streaming: the final text answer is chunked and paced in agent.py
rather than using the SDK's native token stream. Coordinating native
streaming with manual multi-step function calling adds real complexity for
a 24h build; chunking a complete response gives the same "typing" UX in the
chat UI. If you have time left, `client.aio.models.generate_content_stream`
is the upgrade path — same call shape, iterate chunks instead of one response.
"""

from google import genai
from google.genai import types, models, _common  # type: ignore

from app.config import settings

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
        sig = from_object.get('thoughtSignature') or from_object.get('thought_signature')
    elif hasattr(from_object, 'thoughtSignature'):
        sig = getattr(from_object, 'thoughtSignature')
    elif hasattr(from_object, 'thought_signature'):
        sig = getattr(from_object, 'thought_signature')
        
    if sig:
        res['_thought_signature'] = sig
    return res

def patched_Part_from_vertex(api_client, from_object, parent_object=None):
    res = orig_Part_from_vertex(api_client, from_object, parent_object)  # type: ignore
    sig = None
    if isinstance(from_object, dict):
        sig = from_object.get('thoughtSignature') or from_object.get('thought_signature')
    elif hasattr(from_object, 'thoughtSignature'):
        sig = getattr(from_object, 'thoughtSignature')
    elif hasattr(from_object, 'thought_signature'):
        sig = getattr(from_object, 'thought_signature')
        
    if sig:
        res['_thought_signature'] = sig
    return res

models._Part_from_mldev = patched_Part_from_mldev  # type: ignore
models._Part_from_vertex = patched_Part_from_vertex  # type: ignore
def patched_from_response(cls, response, kwargs):
    signatures = []
    
    def extract_signatures(data, path=[]):
        if isinstance(data, dict):
            if '_thought_signature' in data:
                signatures.append((list(path), data.pop('_thought_signature')))
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
            object.__setattr__(obj, 'thought_signature', sig)
            
    return validated

_common.BaseModel._from_response = classmethod(patched_from_response)  # type: ignore

def patched_Part_to_mldev(api_client, from_object, parent_object=None):
    res = orig_Part_to_mldev(api_client, from_object, parent_object)  # type: ignore
    sig = None
    if hasattr(from_object, 'thought_signature'):
        sig = getattr(from_object, 'thought_signature')
    elif isinstance(from_object, dict):
        sig = from_object.get('thought_signature') or from_object.get('thoughtSignature')
        
    if sig:
        res['thoughtSignature'] = sig
    return res

def patched_Part_to_vertex(api_client, from_object, parent_object=None):
    res = orig_Part_to_vertex(api_client, from_object, parent_object)  # type: ignore
    sig = None
    if hasattr(from_object, 'thought_signature'):
        sig = getattr(from_object, 'thought_signature')
    elif isinstance(from_object, dict):
        sig = from_object.get('thought_signature') or from_object.get('thoughtSignature')
        
    if sig:
        res['thoughtSignature'] = sig
    return res

models._Part_to_mldev = patched_Part_to_mldev  # type: ignore
models._Part_to_vertex = patched_Part_to_vertex  # type: ignore
# --- END MONKEY PATCHES ---

_client = genai.Client(api_key=settings.gemini_api_key)

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


async def generate_turn(contents: list[types.Content], tool_declarations: list[dict]):
    """One model turn. Caller inspects response.function_calls vs response.text."""
    config = types.GenerateContentConfig(
        tools=_build_tools(tool_declarations),  # type: ignore
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.2,  # low temperature: this agent generates SQL, precision beats creativity
    )
    return await _client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=config,
    )


def model_turn_content(response) -> types.Content:
    """The model's own turn (may contain a function_call part), to be
    appended to history verbatim before the tool result."""
    return response.candidates[0].content


def function_response_content(name: str, response_data: dict) -> types.Content:
    part = types.Part.from_function_response(name=name, response=response_data)
    return types.Content(role="tool", parts=[part])
