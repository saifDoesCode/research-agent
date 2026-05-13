# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

**CLI agent** (interactive, saves `.md` report to disk):
```bash
source venv/bin/activate
python research_agent.py                  # prompts for topic
python research_agent.py "quantum computing"  # topic as argument
```

**Web app** (Flask + SSE frontend):
```bash
source venv/bin/activate
python app.py          # serves at http://localhost:5000
```

**Testing scripts** (run individually to explore the build-up):
```bash
python testing_scripts/step1_raw_responses.py
python testing_scripts/step2_tool_execution.py
python testing_scripts/step3_agent_loop.py
python testing_scripts/step4_report.py
```

## Environment

API keys go in `.env`:
```
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...
```

Both `research_agent.py` and `app.py` fall back to prompting the user if keys are missing from the environment. The web app also accepts keys from the request body.

## Architecture

The project has two entry points that share the same two-phase pipeline:

**Phase 1 — Agent loop** (`run_agent` / `run_agent_streaming`): An agentic loop that calls Claude with a `web_search` tool. Claude decides when it has enough information and signals completion with `stop_reason == "end_turn"`. The loop is capped at `MAX_ITERATIONS = 10`.

**Phase 2 — Report generation** (`generate_report`): A separate, non-agentic call that takes the raw findings text from Phase 1 and formats it into a structured markdown report with fixed sections (Executive Summary, Key Findings, Current Trends, Implications, Sources).

**CLI (`research_agent.py`)**: Runs the pipeline synchronously and saves the report to a timestamped `.md` file.

**Web app (`app.py`)**: Flask server wrapping the same logic with SSE (`text/event-stream`). `run_agent_streaming` is a generator that yields JSON event lines (`type: status | report | error`). The frontend (`static/app.js`) reads the stream with `ReadableStream`, appends status messages to a progress log, then renders the final report using a custom inline markdown renderer. API keys can be supplied in the request body or via `.env`.

**Testing scripts (`testing_scripts/`)**: Four standalone scripts that incrementally build up the full pipeline — useful as reference when debugging the agent loop or tool-calling mechanics.

## Key constants

| Constant | Location | Default |
|---|---|---|
| `MODEL` | both entry points | `claude-haiku-4-5` |
| `MAX_ITERATIONS` | both entry points | `10` |
| `MAX_SEARCH_RESULTS` | both entry points | `3` |
| content truncation per result | `run_search` | `300` chars |
