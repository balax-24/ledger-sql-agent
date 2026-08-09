import asyncio
import json
from app.agent import run_agent
from dotenv import load_dotenv

load_dotenv()

async def simulate_chat(messages):
    print(f"\n================ USER MESSAGE: {messages[-1]['content']} ================")
    async for event in run_agent(messages):
        evt_type = event["event"]
        evt_data = event["data"]
        if evt_type == "token":
            print(evt_data, end="", flush=True)
        elif evt_type == "tool_call":
            print(f"\n[Tool Call] {evt_data['name']}({evt_data['args']})")
        elif evt_type == "tool_result":
            # Truncate large result data for clean printing
            res_str = str(evt_data['result'])
            if len(res_str) > 300:
                res_str = res_str[:300] + "... [TRUNCATED]"
            print(f"[Tool Result] {evt_data['name']} -> {res_str}")
        elif evt_type == "error":
            print(f"\n[Error] {evt_data['message']}")
        elif evt_type == "done":
            print("\n[Done]")

async def main():
    # Scenario 1: Find top 5 products by revenue
    messages = [
        {"role": "user", "content": "Show me the top 5 products by revenue and generate a bar chart."}
    ]
    await simulate_chat(messages)
    
    # Let's mock a simple conversation turn for the next test
    # In the real app, the frontend maps previous assistant turns to a text summary.
    # Scenario 2: ER diagram
    messages2 = [
        {"role": "user", "content": "Draw me the ER diagram for this database."}
    ]
    await simulate_chat(messages2)

    # Scenario 3: Flowchart
    messages3 = [
        {"role": "user", "content": "Create a flowchart showing how orders flow through our system."}
    ]
    await simulate_chat(messages3)

    # Scenario 4: Intentional bad query to show self-correction / error recovery
    messages4 = [
        {"role": "user", "content": "How many items are in table 'non_existent'?"}
    ]
    await simulate_chat(messages4)

if __name__ == "__main__":
    asyncio.run(main())
