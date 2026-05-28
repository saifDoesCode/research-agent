# app.py — full updated file
import os
import json
import logging
from flask import Flask, request, Response, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient
from core import (
    MODEL, MAX_ITERATIONS, TOOLS,
    run_search, generate_report, call_claude
)
from logging_config import setup_logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()
setup_logging()  # initialise once when Flask starts
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")
CORS(app, origins=os.getenv("ALLOWED_ORIGINS", "*").split(","))

limiter = Limiter(
    get_remote_address,
    app=app
)

def run_agent_streaming(anthropic_client, tavily_client, topic):
    logger.info(f"Streaming agent starting — topic='{topic}'")
    messages = [{"role": "user", "content": f"Research this topic thoroughly: {topic}"}]
    seen_queries = set()
    iteration_count = 0

    yield f"data: {json.dumps({'type': 'status', 'message': f'🔍 Researching: {topic}'})}\n\n"

    while True:
        iteration_count += 1
        logger.debug(f"Iteration {iteration_count} starting")

        if iteration_count > MAX_ITERATIONS:
            logger.warning("Max iterations reached")
            yield f"data: {json.dumps({'type': 'status', 'message': '⚠️ Max iterations reached'})}\n\n"
            break

        try:
            response = call_claude(
                anthropic_client,
                model=MODEL,
                max_tokens=2048,
                tools=TOOLS,
                messages=messages
            )
        except Exception as e:
            logger.exception("Claude API call failed permanently after retries")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            break

        logger.debug(f"Iteration {iteration_count} — stop_reason={response.stop_reason}")
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            raw_findings = ""
            for block in response.content:
                if block.type == "text":
                    raw_findings = block.text

            if not raw_findings:
                logger.error("Agent finished but returned no findings")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Agent finished but returned no findings.'})}\n\n"
                break

            logger.info(f"Research complete — iterations={iteration_count}")
            yield f"data: {json.dumps({'type': 'status', 'message': '✅ Research complete. Generating report...'})}\n\n"

            try:
                report = generate_report(anthropic_client, topic, raw_findings)
            except Exception as e:
                logger.exception("Report generation failed permanently")
                yield f"data: {json.dumps({'type': 'error', 'message': f'Report generation failed: {e}'})}\n\n"
                break

            logger.info("Report generated and streamed to client")
            yield f"data: {json.dumps({'type': 'report', 'content': report})}\n\n"
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    query = block.input["query"]

                    if query in seen_queries:
                        logger.warning(f"Duplicate query skipped — query='{query}'")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Duplicate query skipped."
                        })
                        continue

                    seen_queries.add(query)
                    logger.info(f"Searching — query='{query}'")
                    yield f"data: {json.dumps({'type': 'status', 'message': f'🔧 Searching: {query}'})}\n\n"

                    try:
                        result = run_search(tavily_client, query)
                    except Exception as e:
                        logger.exception(f"Search failed permanently — query='{query}'")
                        result = f"Search failed: {e}"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})


@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/developer")
def developer():
    return send_from_directory(".", "developer-info.html")


@app.route("/research", methods=["POST"])
@limiter.limit("3 per day")  # ← add this line
def research():
    data = request.json
    topic = data.get("topic", "").strip()

    # Keys come from server only — never from the request body
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not topic:
        return {"error": "No topic provided"}, 400
    if not anthropic_key or not tavily_key:
        return {"error": "Server not configured"}, 500


    logger.info(f"Research request received — topic='{topic}'")
    anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
    tavily_client = TavilyClient(api_key=tavily_key)

    return Response(
        run_agent_streaming(anthropic_client, tavily_client, topic),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

if __name__ == "__main__":
    app.run(debug=True, port=5500)