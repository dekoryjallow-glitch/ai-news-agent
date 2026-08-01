# AI News Agent

**Automated research and briefing workflow for AI, GTM and business signals.**

AI News Agent collects articles from configured sources, removes duplicates, scores relevance with an AI model and sends a concise briefing to Slack. A separate mode monitors configured competitors and summarizes notable signals.

> **Status:** Personal automation and reference implementation. It is configurable, but not a hosted service or turnkey product.

## What it does

- Collects items from RSS feeds and web research sources
- Deduplicates previously seen links with a local cache
- Scores and enriches new items with Claude
- Filters low-relevance results
- Formats concise Slack briefings
- Supports a separate competitor-intelligence run
- Includes a dry-run mode that does not send messages
- Can run manually or on a schedule

## Workflow

```text
Sources
   ↓
Collect
   ↓
Deduplicate
   ↓
AI scoring and enrichment
   ↓
Relevance filter
   ↓
Format briefing
   ↓
Slack or dry-run output
```

## Requirements

- Python 3.10+
- Anthropic API key
- Slack incoming webhook
- Optional Tavily API key for additional web research

## Quick start

```powershell
git clone https://github.com/dekoryjallow-glitch/ai-news-agent.git
cd ai-news-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Add your credentials to `.env`:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
TAVILY_API_KEY=your_tavily_api_key_here
```

Never commit the real `.env` file or active credentials.

## Run safely first

A dry run prints the generated Slack blocks without sending anything:

```powershell
python main.py --dry-run
```

Run the competitor-intelligence path without sending:

```powershell
python main.py --competitor --dry-run
```

When the configuration and output look correct:

```powershell
python main.py
```

## Configuration

The main configuration lives in `config/config.yaml`.

It controls:

- Agent name and schedule
- Topic clusters and their weights
- Keywords and relevance bonuses
- RSS sources
- Maximum briefing length
- AI model and prompt
- Slack channel
- Cache retention
- Competitor lists and signal weights

The checked-in configuration is an example of a personalized setup. Review and replace the topics, organizations, competitors and prompts before using it for your own workflow.

## Project structure

```text
ai-news-agent/
├── main.py
├── agent/
│   ├── collector.py
│   ├── cache.py
│   ├── brain.py
│   ├── formatter.py
│   ├── delivery.py
│   ├── competitor_collector.py
│   ├── competitor_brain.py
│   └── competitor_formatter.py
├── config/
│   └── config.yaml
├── tests/
├── .github/
│   └── workflows/
├── .env.example
└── requirements.txt
```

## Operational notes

- The cache prevents the same item from appearing repeatedly.
- Items below the configured relevance threshold are excluded.
- Slack sending happens only when dry-run mode is disabled.
- External APIs may create usage costs.
- Headlines, URLs and generated context are shared with the configured AI and delivery providers.

## Scope

This repository documents a practical personal-intelligence workflow. It focuses on automation, filtering and useful output rather than presenting a commercial product.