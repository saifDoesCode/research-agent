import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient

load_dotenv()

# --- Configuration ---
MAX_ITERATIONS = 10
MAX_SEARCH_RESULTS = 3
MODEL = "claude-haiku-4-5"

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

def get_clients():
    """
    Initialize API clients.
    Allows users to pass their own keys via environment or direct input.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not anthropic_key:
        anthropic_key = input("Enter your Anthropic API key: ").strip()
    if not tavily_key:
        tavily_key = input("Enter your Tavily API key: ").strip()

    return (
        anthropic.Anthropic(api_key=anthropic_key),
        TavilyClient(api_key=tavily_key)
    )

def run_search(tavily_client, query):
    """Execute a Tavily search and return formatted results."""
    try:
        search_response = tavily_client.search(query, max_results=MAX_SEARCH_RESULTS)
        formatted_results = ""
        for result_index, result in enumerate(search_response["results"]):
            formatted_results += f"\nResult {result_index + 1}: {result['title']}\n"
            formatted_results += f"URL: {result['url']}\n"
            formatted_results += f"Summary: {result['content'][:300]}\n"
        return formatted_results
    except Exception as error:
        return f"Search failed: {str(error)}"

def run_agent(anthropic_client, tavily_client, topic):
    """
    Run the research agent loop.
    Searches the web autonomously until it has enough information.
    """
    print(f"\n🔍 Researching: {topic}\n")

    messages = [{"role": "user", "content": f"Research this topic thoroughly: {topic}"}]
    iteration_count = 0

    while True:
        iteration_count += 1
        print(f"--- Iteration {iteration_count} ---")

        if iteration_count > MAX_ITERATIONS:
            print("⚠️  Max iterations reached — stopping research loop")
            break

        try:
            response = anthropic_client.messages.create(
                model=MODEL,
                max_tokens=2048,
                tools=tools,
                messages=messages
            )
        except Exception as error:
            print(f"❌ API call failed: {str(error)}")
            break

        print(f"Stop reason: {response.stop_reason}")
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            print("✅ Research complete\n")
            for block in response.content:
                if block.type == "text":
                    return block.text
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"🔧 Searching: '{block.input['query']}'")
                    search_result = run_search(tavily_client, block.input["query"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": search_result
                    })
            messages.append({"role": "user", "content": tool_results})

    return "Research could not be completed."

def generate_report(anthropic_client, topic, raw_findings):
    """Generate a structured markdown report from raw research findings."""
    print("📝 Generating report...\n")

    report_prompt = f"""You are a professional research analyst.
Using the research findings below, write a structured report on: "{topic}"

Research Findings:
{raw_findings}

Your report must follow this structure:

# {topic}: Research Report

## Executive Summary
(2-3 sentences on the most important findings)

## Key Findings
(The 3-5 most important discoveries)

## Current Trends
(Emerging patterns and directions)

## Implications
(Why this matters and what the reader should take away)

## Sources & Further Reading
(List any URLs mentioned in the findings)

---
*Report generated on {datetime.now().strftime("%B %d, %Y")}*

Be specific — use real facts and details from the research."""

    try:
        report_response = anthropic_client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": report_prompt}]
        )
        return report_response.content[0].text
    except Exception as error:
        return f"Report generation failed: {str(error)}"

def save_report(topic, report):
    """Save the report as a markdown file with a timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{topic.lower().replace(' ', '_')}_{timestamp}.md"
    try:
        with open(filename, "w") as report_file:
            report_file.write(report)
        print(f"💾 Report saved: {filename}")
        return filename
    except Exception as error:
        print(f"❌ Could not save report: {str(error)}")
        return None

def main():
    """Main entry point — runs the full research pipeline."""
    print("=" * 50)
    print("   Personal Research Agent")
    print("=" * 50)

    # Get topic from command line or prompt user
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = input("\nWhat would you like to research? ").strip()

    if not topic:
        print("❌ No topic provided. Exiting.")
        sys.exit(1)

    # Initialize clients
    anthropic_client, tavily_client = get_clients()

    # Run the pipeline
    raw_findings = run_agent(anthropic_client, tavily_client, topic)
    report = generate_report(anthropic_client, topic, raw_findings)
    save_report(topic, report)

    print("\n=== Report Preview ===")
    print(report[:600])
    print("\n... (open the .md file to read the full report)")

if __name__ == "__main__":
    main()