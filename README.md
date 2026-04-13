# Project Predictive Analyzer

An AI-powered project health engine that ingests RAMID Excel workbooks and surfaces dimension-based health scores, a radar chart, and natural-language recommendations — all inside a Chainlit chat session.

> For architecture, data models, key flows, and extension points see [design.md](.kiro/specs/project-predictive-analyzer/design.md).  
> For full feature requirements across all phases see [requirements.md](.kiro/specs/project-predictive-analyzer/requirements.md).

---

## What it does

Upload a RAMID workbook (`.xlsx`) in chat and get back:

- A composite health score (0–100) with RAG status — On Track / At Risk / Critical
- A radar chart across six dimensions: Time, Cost, Scope, People, Dependencies, Risks
- Top-5 contributing factors when the score drops below 70
- An AI-generated executive summary and up to 3 actionable recommendations
- A downloadable HTML report for stakeholder sharing
- Conversational Q&A over the results within the same session

---

## Project layout

```
app.py              # Chainlit entry point — wiring only
ui/
  handlers.py       # Message handling logic
  chart.py          # Radar chart builder
  report.py         # HTML report generator
core/
  models.py         # All Pydantic data models
  parser.py         # RAMID Excel parser
  scorer.py         # Dimension scoring engine
  llm_client.py     # OpenAI structured-output client
  sqlite_data_layer.py  # Chat history persistence
templates/
  report.html       # Jinja2 report template
tests/              # pytest + hypothesis property tests
```

---

## Getting started

```bash
./dev.sh setup      # create venv, install deps, generate .env
./dev.sh            # start Chainlit on http://localhost:8000
```

Other commands:

```bash
./dev.sh test       # run pytest
./dev.sh api        # start FastAPI backend (Phase 4)
./dev.sh all        # start both
```

Login with any username and password `dev`.

---

## Configuration

`.env` requires two values:

```
OPENAI_API_KEY=...
CHAINLIT_AUTH_SECRET=...
```

`dev.sh setup` generates the auth secret automatically. Per-project scoring weights live in `configs/<project_name>.json`; falls back to `configs/default.json`.

---

## Phases

| Phase | Scope |
|---|---|
| 1 — MVP | RAMID ingestion, scoring, radar chart, HTML report, Q&A |
| 2 — Post-Hackathon | SharePoint signals, risk-to-issue prediction, assumption monitoring |
| 3 — Forecasting | Milestone slippage, dependency blockage, scope creep detection |
| 4 — Enterprise | Portfolio aggregation, Jira/ADO live integration, ML scoring engine |

Phase 1 is implemented. Phases 2–4 are extension points — `core/` is designed to accommodate them without structural changes.
