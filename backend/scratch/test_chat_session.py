import asyncio
from google import genai
from google.genai import types
from app.config import settings

async def main():
    client = genai.Client(api_key=settings.gemini_api_key)
    
    config = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="get_schema",
                description="Get the database schema.",
                parameters={"type": "OBJECT", "properties": {}}
            )
        ])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )
    
    # Create the chat session
    chat = client.aio.chats.create(model=settings.gemini_model, config=config)
    
    print("--- FIRST TURN ---")
    try:
        response = await chat.send_message("Show me the database schema.")
        print("Response object:", response)
        print("Response content:", response.candidates[0].content)
        
        # Log the history stored inside chat
        history = chat._curated_history
        print("Chat history after first turn:", history)
    except Exception as e:
        print("First turn failed:", e)
        return

    # Simulate tool result
    print("\n--- SECOND TURN ---")
    tool_result = {"success": True, "tables": ["customers", "orders"]}
    part = types.Part.from_function_response(name="get_schema", response=tool_result)
    
    try:
        # Send the tool result back using send_message
        response2 = await chat.send_message(part)
        print("Response 2:", response2.text)
    except Exception as e:
        print("Second turn failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
