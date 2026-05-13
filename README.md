# Personal Research Agent

An autonomous AI research assistant that searches the web, synthesizes findings, and produces structured markdown reports — available as both a CLI tool and a real-time streaming web app.

---

## What it does

You give it a topic. It figures out what to search, runs multiple queries, reads the results, and decides when it knows enough. Then it writes a professional report.

No manual searching. No copy-pasting. No prompt engineering on your end.

---

## Demo

```
$ python research_agent.py "impact of AI agents on software development"

🔍 Researching: impact of AI agents on software development

--- Iteration 1 ---
Stop reason: tool_use
🔧 Searching: 'AI agents software development 2024'
🔧 Searching: 'autonomous coding assistants productivity impact'

--- Iteration 2 ---
Stop reason: tool_use
🔧 Searching: 'GitHub Copilot developer velocity research'

--- Iteration 3 ---
Stop reason: end_turn
✅ Research complete

📝 Generating report...
💾 Report saved: impact_of_ai_agents_on_software_development_20240315_142301.md
```

---

## Architecture

The project is built around a two-phase pipeline, shared between both entry points.

```
User Input
    │
    ▼
┌─────────────────────────────────────┐
│          Phase 1: Agent Loop        │
│                                     │
│  ┌──────────┐    tool_use   ┌─────┐ │
│  │  Claude  │ ────────────► │Tavily│ │
│  │  Haiku   │ ◄──────────── │Search│ │
│  └──────────┘   results    └─────┘ │
│        │                           │
│        │ end_turn (done)            │
└────────┼────────────────────────────┘
         │
         ▼ raw findings text
┌─────────────────────────────────────┐
│        Phase 2: Report Generation   │
│                                     │
│   Claude formats findings into a    │
│   structured markdown report with   │
│   fixed sections                    │
└─────────────────────────────────────┘
         │
         ▼
   Markdown Report
```

**Phase 1 — Agent loop** (`run_agent` / `run_agent_streaming`): Claude autonomously decides what to search and when to stop. The loop runs until `stop_reason == "end_turn"` or a hard cap of 10 iterations is hit.

**Phase 2 — Report generation** (`generate_report`): A separate, non-agentic call that takes the raw findings and formats them into a consistent structure: Executive Summary → Key Findings → Current Trends → Implications → Sources.

**CLI** (`research_agent.py`): Synchronous pipeline. Saves output to a timestamped `.md` file.

**Web app** (`app.py`): Flask server with Server-Sent Events. Progress streams to the browser in real time as the agent works. API keys can be supplied in the request body or via `.env`.

---

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Anthropic Claude Haiku 4.5 |
| Web search | Tavily API |
| Backend | Python / Flask |
| Streaming | Server-Sent Events (SSE) |
| Frontend | Vanilla JS with `ReadableStream` |
| Font | Agdasima (Google Fonts) |

---

## Getting started

**1. Clone and install dependencies**

```bash
git clone https://github.com/your-username/research-agent
cd research-agent
python -m venv venv
source venv/bin/activate
pip install anthropic tavily-python flask flask-cors python-dotenv
```

**2. Add your API keys**

```bash
cp .env.example .env
# then edit .env with your keys
```

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

You'll need:
- An [Anthropic API key](https://console.anthropic.com/) — for Claude
- A [Tavily API key](https://tavily.com/) — for web search (free tier available)

**3. Run it**

CLI:
```bash
python research_agent.py "quantum computing breakthroughs 2024"
```

Web app:
```bash
python app.py
# open http://localhost:5000
```

---

## Configuration

All key constants live at the top of both entry points:

| Constant | Default | What it controls |
|---|---|---|
| `MODEL` | `claude-haiku-4-5` | Which Claude model to use |
| `MAX_ITERATIONS` | `10` | Hard cap on agent loop cycles |
| `MAX_SEARCH_RESULTS` | `3` | Results fetched per Tavily query |
| Content truncation | `300` chars | Characters kept per search result |

Swap `claude-haiku-4-5` for `claude-sonnet-4-5` or `claude-opus-4-5` for higher-quality reports at increased cost.

---

## Report structure

Every report follows the same format, making outputs predictable and easy to scan:

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

## Project structure

```
├── research_agent.py          # CLI entry point
├── app.py                     # Flask web app
├── static/
│   ├── index.html             # Single-page frontend
│   ├── app.js                 # SSE client + markdown renderer
│   └── style.css              # UI styles
├── testing_scripts/
│   ├── step1_raw_responses.py # Explore raw API responses
│   ├── step2_tool_execution.py# Manual tool call round-trip
│   ├── step3_agent_loop.py    # Basic agent loop
│   └── step4_report.py        # Full pipeline end-to-end
└── .env                       # API keys (git-ignored)
```

The `testing_scripts/` directory is a learning resource — four standalone scripts that build up the full pipeline from first principles. Useful for debugging or understanding how tool-calling works.

---

## How the agentic loop works

Claude doesn't just run one search and stop. Each iteration, it:

1. Reads all previous search results in its context window
2. Decides whether it has enough to write a good report
3. If not, calls `web_search` with a new query it formulates itself
4. Receives the results and repeats

When Claude signals it's done (`stop_reason == "end_turn"`), the raw findings are passed to a second, separate Claude call that formats everything into the final report. Keeping these two phases separate means the formatting step can't get distracted by searching, and the search step doesn't waste tokens on formatting.

---

## License

MIT
