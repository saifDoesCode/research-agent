import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=256,
    messages=[{"role": "user", "content": "What is the capital of France?"}]
)

# Don't just print the answer — inspect the whole object
print("=== Full response object ===")
print(response)

print("\n=== The content list ===")
print(response.content)

print("\n=== The text answer ===")
print(response.content[0].text)

print("\n=== Stop reason ===")
print(response.stop_reason)

print("\n=== Token usage ===")
print(response.usage)

print("\n\n=== Now with a tool defined ===")

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

response2 = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=256,
    tools=tools,
    messages=[{"role": "user", "content": "What are the latest AI news today?"}]
)

print("Stop reason:", response2.stop_reason)
print("Content blocks:", response2.content)



# How to extract the tool call details from the response
for block in response2.content:
    if block.type == "tool_use":
        print("Tool name:", block.name)
        print("Tool input:", block.input)
        print("Tool call ID:", block.id)