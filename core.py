# core.py
import os
import logging
from datetime import datetime
from dataclasses import dataclass
import anthropic
from tavily import TavilyClient
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

# --- Shared Configuration ---
MODEL = "claude-haiku-4-5"
MAX_ITERATIONS = 5
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


# --- Retry Policies ---
#
# Two separate policies:
#   - claude_retry: for Anthropic API calls (RateLimitError, APIStatusError)
#   - search_retry: for Tavily calls (generic Exception, since Tavily
#     doesn't expose typed exceptions)
#
# wait_exponential: first retry after 2s, doubles each time, caps at 30s
# stop_after_attempt: gives up after 4 total tries (1 original + 3 retries)
# before_sleep_log: logs a WARNING before each retry so you can see it happening

claude_retry = retry(
    retry=retry_if_exception_type((
        anthropic.RateLimitError,
        anthropic.APIStatusError,
        anthropic.APIConnectionError,
    )),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True   # if all retries fail, re-raise the original exception
)

search_retry = retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

# --- Retryable API Wrappers ---

@claude_retry
def call_claude(anthropic_client: anthropic.Anthropic, **kwargs):
    """
    Single wrapper for all Anthropic calls.
    Retries on rate limits and transient API errors.
    Also logs token usage on every successful call.
    """
    response = anthropic_client.messages.create(**kwargs)
    logger.info(
        f"Claude call succeeded — model={kwargs.get('model')}, "
        f"input_tokens={response.usage.input_tokens}, "
        f"output_tokens={response.usage.output_tokens}"
    )
    return response

# core.py — update run_search exception handling
@search_retry
def run_search(tavily_client: TavilyClient, query: str) -> str:
    """Execute a Tavily search and return formatted results."""
    logger.debug(f"Running search — query='{query}'")
    try:
        search_response = tavily_client.search(query, max_results=MAX_SEARCH_RESULTS)
        formatted_results = ""
        for i, result in enumerate(search_response["results"]):
            formatted_results += f"\nResult {i + 1}: {result['title']}\n"
            formatted_results += f"URL: {result['url']}\n"
            formatted_results += f"Summary: {result['content'][:300]}\n"
        logger.info(f"Search succeeded — query='{query}', results={len(search_response['results'])}")
        return formatted_results
    except Exception:
        # logger.exception logs the full traceback automatically
        logger.exception(f"Search failed — query='{query}'")
        raise  # let tenacity handle retries


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