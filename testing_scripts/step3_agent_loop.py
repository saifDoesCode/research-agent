import os
from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

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

def run_search(query):
    """Execute a Tavily search and return formatted results."""
    search_response = tavily.search(query, max_results=3)
    formatted_results = ""
    
    for result_index, result in enumerate(search_response["results"]):
        formatted_results += f"\nResult {result_index + 1}: {result['title']}\n"
        formatted_results += f"URL: {result['url']}\n"
        formatted_results += f"Summary: {result['content'][:300]}\n"
    
    return formatted_results

def run_agent(user_question):
    """Run the agent loop until the model produces a final answer."""
    print(f"\n🔍 Research question: {user_question}\n")
    
    messages = [{"role": "user", "content": user_question}]
    loop_count = 0

    while True:
        loop_count += 1
        print(f"--- Loop iteration {loop_count} ---")

        # Call the model
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        print(f"Stop reason: {response.stop_reason}")

        # Append assistant response to history
        messages.append({"role": "assistant", "content": response.content})

        # If done, extract and return the final text
        if response.stop_reason == "end_turn":
            print("\n✅ Agent finished.\n")
            for block in response.content:
                if block.type == "text":
                    return block.text

        # If tool use, handle every tool call in this response
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    print(f"🔧 Calling tool: {block.name}(query='{block.input['query']}')")
                    result = run_search(block.input["query"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Send all tool results back in one user message
            messages.append({"role": "user", "content": tool_results})

# --- Run it ---
answer = run_agent("What are the latest developments in AI agents?")
print("=== Final Answer ===")
print(answer)