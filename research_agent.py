# research_agent.py — full updated file
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient

from core import (
    MODEL, MAX_ITERATIONS, TOOLS,
    AgentResult, run_search, generate_report, call_claude
)
from logging_config import setup_logging
import logging

load_dotenv()
setup_logging(debug="--debug" in sys.argv)
logger = logging.getLogger(__name__)


def get_clients():
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


def run_agent(anthropic_client, tavily_client, topic) -> AgentResult:
    logger.info(f"Agent starting — topic='{topic}'")
    messages = [{"role": "user", "content": f"Research this topic thoroughly: {topic}"}]
    seen_queries = set()
    iteration_count = 0

    while True:
        iteration_count += 1
        logger.debug(f"Iteration {iteration_count} starting")

        if iteration_count > MAX_ITERATIONS:
            logger.warning(f"Max iterations ({MAX_ITERATIONS}) reached — stopping")
            return AgentResult(
                success=False, findings="",
                iterations=iteration_count,
                error="Max iterations reached"
            )

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
            return AgentResult(
                success=False, findings="",
                iterations=iteration_count,
                error=str(e)
            )

        logger.debug(f"Iteration {iteration_count} — stop_reason={response.stop_reason}")
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            logger.info(f"Research complete — iterations={iteration_count}")
            for block in response.content:
                if block.type == "text":
                    return AgentResult(
                        success=True,
                        findings=block.text,
                        iterations=iteration_count
                    )

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

    return AgentResult(success=False, findings="", iterations=iteration_count, error="Unexpected exit")


def save_report(topic: str, report: str) -> str | None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{topic.lower().replace(' ', '_')}_{timestamp}.md"
    try:
        with open(filename, "w") as f:
            f.write(report)
        logger.info(f"Report saved — file={filename}")
        return filename
    except Exception:
        logger.exception("Failed to save report")
        return None


def main():
    logger.info("Research Agent starting")

    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("\nWhat would you like to research? ").strip()

    if not topic:
        logger.error("No topic provided — exiting")
        sys.exit(1)

    anthropic_client, tavily_client = get_clients()

    # Phase 1
    result = run_agent(anthropic_client, tavily_client, topic)

    if not result.success:
        logger.error(f"Research failed — reason='{result.error}', iterations={result.iterations}")
        sys.exit(1)

    # Phase 2
    logger.info("Generating report")
    try:
        report = generate_report(anthropic_client, topic, result.findings)
    except Exception:
        logger.exception("Report generation failed permanently")
        sys.exit(1)

    save_report(topic, report)

    print("\n=== Report Preview ===")
    print(report[:600])
    print("\n... (open the .md file to read the full report)")


if __name__ == "__main__":
    main()