import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")

url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

payload = {
    "contents": [
        {
            "role": "user",
            "parts": [
                {"text": "Show me the database schema."}
            ]
        }
    ],
    "tools": [
        {
            "functionDeclarations": [
                {
                    "name": "get_schema",
                    "description": "Get the database schema.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {}
                    }
                }
            ]
        }
    ],
    "toolConfig": {
        "functionCallingConfig": {
            "mode": "ANY",
            "allowedFunctionNames": ["get_schema"]
        }
    }
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, json=payload)
print("Status Code:", response.status_code)
print("Response JSON:")
print(json.dumps(response.json(), indent=2))
