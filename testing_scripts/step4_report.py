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
    """Run the agent loop and return the raw findings."""
    print(f"\n🔍 Researching: {user_question}\n")

    messages = [{"role": "user", "content": user_question}]
    loop_count = 0

    while True:
        loop_count += 1
        print(f"--- Loop iteration {loop_count} ---")

        # Safety guard your senior engineer would approve of
        if loop_count > 10:
            print("⚠️ Max iterations reached")
            break

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            tools=tools,
            messages=messages
        )

        print(f"Stop reason: {response.stop_reason}")
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            print("✅ Research complete\n")
            for block in response.content:
                if block.type == "text":
                    return block.text

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"🔧 Searching: '{block.input['query']}'")
                    search_result = run_search(block.input["query"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": search_result
                    })
            messages.append({"role": "user", "content": tool_results})

def generate_report(topic, raw_findings):
    """Take raw research findings and write a structured report."""
    print("📝 Generating structured report...\n")

    report_prompt = f"""You are a professional research analyst. 
Using the research findings below, write a structured report on the topic: "{topic}"

Research Findings:
{raw_findings}

Your report must follow this exact structure:

# {topic}: Research Report

## Executive Summary
(2-3 sentences summarizing the most important findings)

## Key Findings
(The 3-5 most important discoveries from the research)

## Current Trends
(What patterns or directions are emerging)

## Implications
(Why this matters — what should the reader take away)

## Sources & Further Reading
(List any URLs mentioned in the findings)

Write clearly and professionally. Be specific — use facts and details from the research, not vague generalities."""

    report_response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": report_prompt}]
    )

    return report_response.content[0].text

def save_report(topic, report):
    """Save the report to a markdown file."""
    filename = topic.lower().replace(" ", "_") + "_report.md"
    with open(filename, "w") as report_file:
        report_file.write(report)
    print(f"💾 Report saved to: {filename}")
    return filename

# --- Run the full pipeline ---
topic = "the impact of AI agents on software development"

raw_findings = run_agent(topic)
report = generate_report(topic, raw_findings)
save_report(topic, report)

print("\n=== Report Preview ===")
print(report[:500], "...")