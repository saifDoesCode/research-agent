# Personal Research Agent

An agentic AI research assistant powered by **Claude Haiku** and **Tavily Search**. Give it a topic — it autonomously decides what to search, runs multiple live web queries, synthesises the findings, and delivers a structured markdown report in real time. Available as both a streaming web app and an interactive CLI.

---

## How It Works

The pipeline runs in two distinct phases, shared between both entry points:

**Phase 1 — Agent Loop**

An agentic loop drives Claude Haiku with a `web_search` tool. Claude autonomously decides what queries to run, inspects the results, and issues further searches until it determines it has enough information — signalled by `stop_reason == "end_turn"`. The loop is hard-capped at 10 iterations to bound cost and latency.

**Phase 2 — Report Generation**

A separate, non-agentic call takes the raw findings text and formats it into a structured markdown report with five fixed sections: Executive Summary, Key Findings, Current Trends, Implications, and Sources & Further Reading. Keeping these phases separate prevents the formatting step from interfering with search behaviour and avoids burning tokens on structure during research.

```
Browser / CLI
     │
     │  POST /research (topic)
     ▼
Flask Server  ──────────────────────────────────────────────────────────┐
     │                                                                   │
     │  Phase 1: Agent Loop (run_agent_streaming)                        │
     │      ├─ messages.create() ──────────────► Claude Haiku            │
     │      │          ◄── tool_use / end_turn ─────────────────────     │
     │      └─ tavily.search(query) ──────────► Tavily Search API        │
     │                 ◄── results ───────────────────────────────────   │
     │                                                                   │
     │  Phase 2: Report Generation (generate_report)                     │
     │      └─ messages.create() ──────────────► Claude Haiku            │
     │                 ◄── structured markdown ───────────────────────   │
     │                                                                   │
     │  SSE stream: status events → report event → browser              │
     ▼                                                                   │
Browser (ReadableStream → inline markdown renderer → downloadable .md) ─┘
```

---

## Features

- **Autonomous research loop** — Claude decides what to search and when to stop, with zero hardcoded query logic
- **Real-time streaming** — Server-Sent Events push live progress updates to the browser as the agent works (`Searching: X…`, `Research complete`, etc.)
- **Structured reports** — Consistent five-section markdown format, downloadable as `.md`
- **Duplicate query detection** — An in-memory `seen_queries` set prevents Claude from re-issuing the same search within a session
- **Dual entry points** — Full-featured web app and a standalone CLI that saves timestamped reports to disk
- **Rate limiting** — 3 research requests per IP per day via `flask-limiter`, with a polished in-app modal when the limit is hit
- **Structured logging** — Dual-handler logging to console and daily rotating log files with per-module context and token usage tracking
- **Secure by design** — API keys live server-side only; the frontend never sees or sends credentials

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Model | Claude Haiku (`claude-haiku-4-5`) via Anthropic SDK |
| Web Search | Tavily Search API |
| Backend | Python 3.11 · Flask 3 · flask-limiter · flask-cors |
| Streaming | Server-Sent Events (`text/event-stream`) |
| Frontend | Vanilla JS · Fetch API · `ReadableStream` |
| Config | `python-dotenv` — keys server-side only, never exposed to client |
| Logging | Python `logging` — structured format, dual handlers (console + daily file) |

---

## Error Handling & Resilience

Every failure path is handled explicitly. A single failed search or transient API error never brings down the whole pipeline.

### Agent Loop

| Scenario | Handling |
|---|---|
| **Claude API call fails** | Exception caught and logged with full traceback. CLI exits with code 1. Web app emits an SSE `error` event to the browser — the stream closes cleanly and the UI displays the error message. |
| **Individual Tavily search fails** | Exception caught _per query_. A `"Search failed: <reason>"` string is returned as the tool result so Claude can continue with remaining queries instead of aborting the entire loop. |
| **Duplicate search query** | Detected via `seen_queries` set before the network call is made. Skipped with an informational tool result and a `WARNING` log entry. Prevents redundant API calls and infinite search loops. |
| **Max iterations exceeded (10)** | Loop terminates gracefully, warning logged. Returns a failed `AgentResult` with `error="Max iterations reached"`. |
| **Agent ends turn with no text** | Explicit post-`end_turn` check. If no text block is found in the response, an SSE `error` event is emitted rather than silently calling report generation with empty content. |

### Report Generation

| Scenario | Handling |
|---|---|
| **Claude API call fails** | Exception caught and logged. CLI exits with code 1. Web app emits SSE `error` event. |
| **File write fails (CLI)** | Exception caught and logged. The report is still printed to stdout, so no work is lost even if the filesystem write fails. |

### HTTP Layer

| Scenario | Handling |
|---|---|
| **Rate limit exceeded (3/day/IP)** | `flask-limiter` returns HTTP 429. The frontend checks `response.status` _before_ opening the SSE stream and shows a modal dialog explaining the limit and reset time — no broken stream, no silent failure. |
| **Missing server API keys** | Returns HTTP 500 with `{"error": "Server not configured"}`. Keys are never accepted from the request body. |
| **Empty topic submitted** | Returns HTTP 400 with `{"error": "No topic provided"}`. |
| **Partial SSE frame received** | Each JSON parse in the frontend stream reader is wrapped in `try/catch`. Malformed partial frames are silently discarded without breaking the stream. |

### Logging

Every event — success or failure — is written to both stdout and a daily log file (`logs/app_YYYYMMDD.log`). Third-party loggers (`httpx`, `httpcore`, `anthropic`) are silenced to `WARNING` to keep the signal-to-noise ratio high.

```
2026-05-25 11:43:01 | INFO     | app                  | Research request received — topic='quantum computing'
2026-05-25 11:43:02 | INFO     | core                 | Searching — query='quantum computing breakthroughs 2025'
2026-05-25 11:43:03 | INFO     | core                 | Searching — query='quantum hardware IBM Google 2025'
2026-05-25 11:43:05 | WARNING  | core                 | Duplicate query skipped — query='quantum computing'
2026-05-25 11:43:09 | INFO     | core                 | Research complete — iterations=4
2026-05-25 11:43:11 | INFO     | core                 | Report generated — tokens used: input=3821, output=612
```

---

## Project Structure

```
research-agent/
├── app.py                    # Flask web server — SSE streaming endpoint, rate limiting
├── research_agent.py         # CLI entry point — synchronous pipeline, saves .md to disk
├── core.py                   # Shared pipeline: call_claude, run_search, generate_report
├── logging_config.py         # Dual-handler logging setup (console + daily rotating file)
├── static/
│   ├── index.html            # Single-page app
│   ├── app.js                # SSE consumer, markdown renderer, rate-limit modal, UI logic
│   ├── style.css             # Styling
│   └── systemdesign.png      # Architecture diagram
├── developer-info.html       # Developer contact page (loaded in modal iframe)
├── testing_scripts/          # Standalone incremental build-up scripts for debugging
│   ├── step1_raw_responses.py
│   ├── step2_tool_execution.py
│   ├── step3_agent_loop.py
│   └── step4_report.py
├── logs/                     # Daily rotating log files (auto-created at runtime)
├── .env                      # API keys — never committed
└── requirements.txt
```

---

## Getting Started

**1. Clone and install**
```bash
git clone <repo-url>
cd research-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Add API keys**
```
# .env
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

Get yours at:
- **Anthropic** — [console.anthropic.com](https://console.anthropic.com)
- **Tavily** — [app.tavily.com](https://app.tavily.com)

**3. Run**

```bash
# Web app — serves at http://localhost:5500
python app.py

# CLI — interactive prompt
python research_agent.py

# CLI — topic as argument
python research_agent.py "large language model scaling laws"

# CLI — verbose debug logging
python research_agent.py "fusion energy" --debug
```

---

## Report Format

Every report follows the same five-section structure:

```markdown
# {Topic}: Research Report

## Executive Summary
## Key Findings
## Current Trends
## Implications
## Sources & Further Reading

---
*Report generated on {date}*
```

---

## Key Constants

| Constant | Default | Description |
|---|---|---|
| `MODEL` | `claude-haiku-4-5` | Anthropic model used for both phases |
| `MAX_ITERATIONS` | `10` | Hard cap on agent loop cycles |
| `MAX_SEARCH_RESULTS` | `3` | Tavily results returned per query |
| Content truncation | `300 chars` | Per-result content limit passed to Claude |
| Rate limit | `3 / day / IP` | Enforced server-side by `flask-limiter` |

---

## Developer

**Saif Ahmed**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-saif--ahmed-blue?style=flat&logo=linkedin)](https://www.linkedin.com/in/saif-ahmed-6ba859257/)
[![Portfolio](https://img.shields.io/badge/Portfolio-visit-orange?style=flat)](https://personal-portfolio-2026-xi.vercel.app)
[![Email](https://img.shields.io/badge/Email-saifanis03%40gmail.com-red?style=flat&logo=gmail)](mailto:saifanis03@gmail.com)

---

## License

MIT
