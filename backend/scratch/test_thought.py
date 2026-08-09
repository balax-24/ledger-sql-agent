import asyncio
import os
from google import genai
from google.genai import types, models, _common
from dotenv import load_dotenv

load_dotenv()

# --- MONKEY PATCHES START ---
orig_Part_from_mldev = models._Part_from_mldev
orig_Part_from_vertex = models._Part_from_vertex
orig_Part_to_mldev = models._Part_to_mldev
orig_Part_to_vertex = models._Part_to_vertex
orig_from_response = _common.BaseModel._from_response

def patched_Part_from_mldev(api_client, from_object, parent_object=None):
    res = orig_Part_from_mldev(api_client, from_object, parent_object)
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
    res = orig_Part_from_vertex(api_client, from_object, parent_object)
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

models._Part_from_mldev = patched_Part_from_mldev
models._Part_from_vertex = patched_Part_from_vertex

@classmethod
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
    
    validated = orig_from_response.__func__(cls, response, kwargs)
    
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

_common.BaseModel._from_response = patched_from_response

def patched_Part_to_mldev(api_client, from_object, parent_object=None):
    res = orig_Part_to_mldev(api_client, from_object, parent_object)
    sig = None
    if hasattr(from_object, 'thought_signature'):
        sig = getattr(from_object, 'thought_signature')
    elif isinstance(from_object, dict):
        sig = from_object.get('thought_signature') or from_object.get('thoughtSignature')
        
    if sig:
        res['thoughtSignature'] = sig
    return res

def patched_Part_to_vertex(api_client, from_object, parent_object=None):
    res = orig_Part_to_vertex(api_client, from_object, parent_object)
    sig = None
    if hasattr(from_object, 'thought_signature'):
        sig = getattr(from_object, 'thought_signature')
    elif isinstance(from_object, dict):
        sig = from_object.get('thought_signature') or from_object.get('thoughtSignature')
        
    if sig:
        res['thoughtSignature'] = sig
    return res

models._Part_to_mldev = patched_Part_to_mldev
models._Part_to_vertex = patched_Part_to_vertex
# --- MONKEY PATCHES END ---

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

async def test():
    tool_declarations = [
        types.FunctionDeclaration(
            name="get_schema",
            description="Get the database schema.",
            parameters=types.Schema(type="OBJECT", properties={}, required=[])
        )
    ]
    tools = [types.Tool(function_declarations=tool_declarations)]
    
    config = types.GenerateContentConfig(
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.2,
    )
    
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text="How many tables are in the database?")])
    ]
    
    print("--- FIRST TURN ---")
    response = await client.aio.models.generate_content(
        model=os.environ["GEMINI_MODEL"],
        contents=contents,
        config=config,
    )
    
    cand_content = response.candidates[0].content
    print("Candidate:", response.candidates[0].model_dump())
    print("Model content:", cand_content)
    for part in cand_content.parts:
        if part.function_call:
            print("Function Call:", part.function_call)
            print("Function Call fields:", part.function_call.model_dump())
            print("Part has thought_signature attribute:", getattr(part, "thought_signature", None))
            
    contents.append(cand_content)
    
    # Simulate tool result
    tool_result = {"success": True, "tables": ["customers", "orders"]}
    part = types.Part.from_function_response(name="get_schema", response=tool_result)
    contents.append(types.Content(role="tool", parts=[part]))
    
    print("\n--- SECOND TURN ---")
    try:
        response2 = await client.aio.models.generate_content(
            model=os.environ["GEMINI_MODEL"],
            contents=contents,
            config=config,
        )
        print("Second turn success!")
        print("Response text:", response2.text)
    except Exception as exc:
        print("Second turn failed:", exc)

asyncio.run(test())
