import os
import json
from flask import Flask, request, Response, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient

load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)

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

# --- Agent functions (same logic as before, adapted for streaming) ---

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

def run_agent_streaming(anthropic_client, tavily_client, topic):
    messages = [{"role": "user", "content": f"Research this topic thoroughly: {topic}"}]
    iteration_count = 0

    yield f"data: {json.dumps({'type': 'status', 'message': f'🔍 Researching: {topic}'})}\n\n"

    while True:
        iteration_count += 1

        if iteration_count > MAX_ITERATIONS:
            yield f"data: {json.dumps({'type': 'status', 'message': '⚠️ Max iterations reached'})}\n\n"
            break

        try:
            response = anthropic_client.messages.create(
                model=MODEL,
                max_tokens=2048,
                tools=tools,
                messages=messages
            )
        except Exception as error:
            yield f"data: {json.dumps({'type': 'error', 'message': str(error)})}\n\n"
            break

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            raw_findings = ""
            for block in response.content:
                if block.type == "text":
                    raw_findings = block.text

            yield f"data: {json.dumps({'type': 'status', 'message': '✅ Research complete. Generating report...'})}\n\n"

            report = generate_report(anthropic_client, topic, raw_findings)
            yield f"data: {json.dumps({'type': 'report', 'content': report})}\n\n"
            break

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    search_message = f"🔧 Searching: {block.input['query']}"
                    yield f"data: {json.dumps({'type': 'status', 'message': search_message})}\n\n"

                    search_result = run_search(tavily_client, block.input["query"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": search_result
                    })

            messages.append({"role": "user", "content": tool_results})

def generate_report(anthropic_client, topic, raw_findings):
    """Generate a structured markdown report from raw research findings."""
    from datetime import datetime

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

# --- Flask routes ---

@app.route("/")
def index():
    """Serve the frontend."""
    return send_from_directory("static", "index.html")

@app.route("/research", methods=["POST"])
def research():
    """
    Receive a topic and API keys from the frontend,
    run the agent, and stream progress back.
    """
    data = request.json
    topic = data.get("topic", "").strip()
    anthropic_key = data.get("anthropic_key", "").strip() or os.getenv("ANTHROPIC_API_KEY")
    tavily_key = data.get("tavily_key", "").strip() or os.getenv("TAVILY_API_KEY")

    if not topic:
        return {"error": "No topic provided"}, 400
    if not anthropic_key or not tavily_key:
        return {"error": "API keys missing"}, 400

    anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
    tavily_client = TavilyClient(api_key=tavily_key)

    return Response(
        run_agent_streaming(anthropic_client, tavily_client, topic),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    app.run(debug=True, port=5500)