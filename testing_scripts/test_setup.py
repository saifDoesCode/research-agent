import os
from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient

load_dotenv()

# Test Anthropic
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
message = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=64,
    messages=[{"role": "user", "content": "Say: setup works!"}]
)
print("Anthropic:", message.content[0].text)

# Test Tavily
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
results = tavily.search("latest AI news", max_results=1)
print("Tavily:", results['results'][0]['title'])