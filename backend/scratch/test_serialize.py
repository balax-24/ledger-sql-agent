import json
from google.genai import types

def test():
    part = types.Part.from_text(text="hello")
    print("Part model_dump:", part.model_dump())
    print("Part model_dump_json:", part.model_dump_json())

    fc = types.FunctionCall(name="get_schema", id="some_id", args={})
    print("FunctionCall dump:", fc.model_dump())
    
    p = types.Part(function_call=fc)
    print("Part with FunctionCall dump:", p.model_dump(exclude_none=True))
    
    # Let's inspect all fields of types.FunctionCall or check if it accepts other keyword arguments
    try:
        fc2 = types.FunctionCall(name="get_schema", id="some_id", thought_signature="sig", args={})
        print("Success with thought_signature")
    except Exception as e:
        print("Error with thought_signature:", e)

    try:
        fc3 = types.FunctionCall(name="get_schema", id="some_id", thoughtSignature="sig", args={})
        print("Success with thoughtSignature")
    except Exception as e:
        print("Error with thoughtSignature:", e)

if __name__ == "__main__":
    test()
