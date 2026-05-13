import os
import json
from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# --- Step 1: Define the tool ---
tools = [
    {
        "name": "web_search",
        "description": "Search the web for current information on a topic",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    }
]

# --- Step 2: First API call - model decides to use tool ---
print("=== Turn 1: Sending user message ===")
messages = [{"role": "user", "content": "What are the latest developments in AI agents?"}]

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    tools=tools,
    messages=messages
)

print("Stop reason:", response.stop_reason)

# --- Step 3: Extract the tool call ---
tool_use_block = None
for block in response.content:
    if block.type == "tool_use":
        tool_use_block = block
        print(f"Model wants to call: {block.name}(query='{block.input['query']}')")

# --- Step 4: Actually execute the search ---
print("\n=== Turn 2: Executing the search ===")
search_results = tavily.search(tool_use_block.input["query"], max_results=3)

# Format results into a readable string
formatted_results = ""
for i, result in enumerate(search_results["results"]):
    formatted_results += f"\nResult {i+1}: {result['title']}\n"
    formatted_results += f"URL: {result['url']}\n"
    formatted_results += f"Summary: {result['content'][:300]}\n"

print("Search returned", len(search_results["results"]), "results")
print(formatted_results[:500], "...")

# --- Step 5: Send results back to the model ---
print("\n=== Turn 3: Sending results back to model ===")

# Append assistant's response to message history
messages.append({"role": "assistant", "content": response.content})

# Append the tool result as a user message
messages.append({
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": tool_use_block.id,  # must match the tool call ID
            "content": formatted_results
        }
    ]
})

# --- Step 6: Second API call - model reads results and answers ---
response2 = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    tools=tools,
    tool_choice={"type": "none"},  # forces text answer, no more tool calls
    messages=messages
)

print("Stop reason:", response2.stop_reason)
print("\n=== Final Answer ===")
for block in response2.content:
    if block.type == "text":
        print(block.text)