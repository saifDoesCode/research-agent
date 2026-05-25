# core.py
import os
import logging
from datetime import datetime
from dataclasses import dataclass
import anthropic
from tavily import TavilyClient

logger = logging.getLogger(__name__)

# --- Shared Configuration ---
MODEL = "claude-haiku-4-5"
MAX_ITERATIONS = 10
MAX_SEARCH_RESULTS = 3

TOOLS = [
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

# --- Agent Result Contract ---
@dataclass
class AgentResult:
    success: bool
    findings: str
    iterations: int
    error: str = ""


def call_claude(anthropic_client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    """Thin wrapper around messages.create for easy mocking and retry handling."""
    return anthropic_client.messages.create(**kwargs)


def run_search(tavily_client: TavilyClient, query: str) -> str:
    """Execute a Tavily search and return formatted results."""
    try:
        search_response = tavily_client.search(query, max_results=MAX_SEARCH_RESULTS)
        formatted_results = ""
        for i, result in enumerate(search_response["results"]):
            formatted_results += f"\nResult {i + 1}: {result['title']}\n"
            formatted_results += f"URL: {result['url']}\n"
            formatted_results += f"Summary: {result['content'][:300]}\n"
        return formatted_results
    except Exception as e:
        logger.exception(f"Search failed for query '{query}'")
        raise


def generate_report(anthropic_client: anthropic.Anthropic, topic: str, raw_findings: str) -> str:
    """Generate a structured markdown report from raw research findings."""
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
        response = anthropic_client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": report_prompt}]
        )
        logger.info(f"Report generated — tokens used: input={response.usage.input_tokens}, output={response.usage.output_tokens}")
        return response.content[0].text
    except Exception as e:
        logger.exception("Report generation failed")
        raise