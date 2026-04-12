# Design Document — Project Predictive Analyzer

## Overview

The Project Predictive Analyzer is a Chainlit chat application that ingests a RAMID Excel workbook, scores project health across six dimensions, renders a radar chart, and delivers an HTML executive report — all within a single chat session. Follow-up questions are answered using session-stored context.

**Phase 1 scope only.** Phases 2–4 are called out as extension points.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Chainlit Chat UI                      │
│  app.py — on_message / on_chat_start / cl.user_session  │
│  ui/chart.py — cl.Plotly radar chart                    │
│  ui/report.py — cl.File HTML report                     │
└────────────────────┬────────────────────────────────────┘
                     │ calls into core/ (no cl.* imports)
          ┌──────────▼──────────────────────────────────┐
          │                  core/                       │
          │  models.py   — all Pydantic data models      │
          │  parser.py   — RAMID_Parser                  │
          │  scorer.py   — Scoring_Engine                │
          │  llm_client.py — LLM_Client                  │
          │  config.py   — ThresholdConfig loader        │
          └─────────────────────────────────────────────┘
```

**Rule:** `core/` has zero Chainlit imports. `app.py` and `ui/` are the only files that touch `cl.*`. This keeps the backend independently testable and swappable — a FastAPI layer can be added in Phase 4 by wrapping `core/` without touching any existing code.

**File layout:**

```
app.py                  # Chainlit entry point, message handlers
mock_data.py            # Hardcoded AnalysisResult for UI development

ui/
  chart.py              # build_radar() → go.Figure (wrapped in cl.Plotly by app.py)
  report.py             # generate_html() → str (written to cl.File by app.py)

core/
  models.py             # RAMIDData, AnalysisResult, ThresholdConfig, etc.
  parser.py             # RAMID_Parser — parse() + format_for_llm()
  scorer.py             # Scoring_Engine — score() + dimension scorers
  llm_client.py         # LLM_Client — analyze() + answer()
  config.py             # ThresholdConfig loader (JSON files)

templates/
  report.html           # Jinja2 report template

configs/
  default.json          # Default ThresholdConfig

tests/
  test_parser.py
  test_scorer.py
  test_llm_client.py
  test_report.py

# Future (Phase 4 — React-ready):
# api/
#   main.py             # FastAPI wrapper around core/ — zero changes to core/
# frontend/             # React app calling api/
```

---

## Components and Interfaces

### app.py — Chainlit Entry Point

Handles Chainlit lifecycle hooks and orchestrates the main flow. Only file that imports both `cl.*` and `core/`.

```python
@cl.on_chat_start  # initialise session
@cl.on_message     # route: file upload → analysis flow; text → Q&A flow
```

Session keys stored in `cl.user_session`:
- `ramid_data: RAMIDData`
- `analysis_result: AnalysisResult`
- `conversation_history: list[dict]`

### ui/chart.py — Radar Chart Builder

```python
def build_radar(result: AnalysisResult) -> go.Figure: ...
```

- Returns a `go.Figure` (Scatterpolar). `app.py` wraps it in `cl.Plotly`.
- Color driven by RAG status: green / amber / red.
- No Chainlit imports.

### ui/report.py — Report Generator

```python
def generate_html(result: AnalysisResult, project_name: str) -> str: ...
```

- Renders `templates/report.html` via Jinja2 with inline styles.
- `app.py` writes output to a temp file and delivers as `cl.File`.
- No Chainlit imports.

### core/parser.py — RAMID_Parser

```python
def parse(file_path: str) -> RAMIDData: ...
def format_for_llm(data: RAMIDData) -> str: ...
```

- Uses `pd.read_excel(path, sheet_name=None)` to load all sheets at once.
- Resolves Risk Severity via Risk Chart lookup (`probability × impact → severity`).
- Raises `ParseError` (subclass of `ValueError`) with sheet/column info on bad input.

### core/scorer.py — Scoring_Engine

```python
def score(data: RAMIDData, config: ThresholdConfig) -> AnalysisResult: ...
def _top_factors(signals: list[ScoringSignal], n: int = 5) -> list[ContributingFactor]: ...
```

- Each dimension is a private function `_score_<dimension>(data, config) -> float`.
- Adding a new dimension = add one `_score_X` function and register it in a `DIMENSION_SCORERS` dict — no other changes needed.
- Returns `contributing_factors` only when `composite < 70`.

### core/llm_client.py — LLM_Client

```python
async def analyze(data: RAMIDData, result: AnalysisResult) -> LLMResponse: ...
async def answer(question: str, context: AnalysisResult, history: list[dict]) -> str: ...
```

- Uses `openai.AsyncOpenAI` with `response_format=LLMResponse` (Pydantic structured output).
- Temperature fixed at `0.2`.
- Raises `LLMError` on API failure, preserving raw response when parse fails.

### core/config.py — ThresholdConfig Loader

```python
def load_config(project_name: str) -> ThresholdConfig: ...
```

- Looks for `configs/{project_name}.json`; falls back to `configs/default.json`.
- Validates via Pydantic on load.

---

## Data Models

```python
# models.py

from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import date

# ── Raw parsed data ──────────────────────────────────────

class RiskRow(BaseModel):
    id: str
    impact: str
    probability: str
    severity: str          # resolved from Risk Chart
    status: str
    owner: str
    date_raised: Optional[date]
    date_closed: Optional[date]

class IssueRow(BaseModel):
    id: str
    priority: str
    root_cause: str
    status: str
    date_raised: Optional[date]
    date_due: Optional[date]
    date_resolved: Optional[date]

class MilestoneRow(BaseModel):
    name: str
    phase: str
    due_date: Optional[date]
    at_risk: bool
    status: str            # Achieved / Planned / Cancelled

class DependencyRow(BaseModel):
    id: str
    importance: str        # Very High / High / Medium
    due_date: Optional[date]
    date_completed: Optional[date]
    status: str

class AssumptionRow(BaseModel):
    id: str
    criticality: str
    validation_due: Optional[date]
    date_validated: Optional[date]
    validated: bool

class ActionItemRow(BaseModel):
    id: str
    owner: str
    due_date: Optional[date]
    date_completed: Optional[date]
    status: str

class KPIRow(BaseModel):
    month: str
    dimension: str         # e.g. "Excellence in Delivery"
    metric: str
    value: float

class RAMIDData(BaseModel):
    project_name: str = "Unknown"
    risks: list[RiskRow] = []
    issues: list[IssueRow] = []
    milestones: list[MilestoneRow] = []
    dependencies: list[DependencyRow] = []
    assumptions: list[AssumptionRow] = []
    action_items: list[ActionItemRow] = []
    kpi_rows: list[KPIRow] = []

# ── Config ───────────────────────────────────────────────

class ThresholdConfig(BaseModel):
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "time": 1/6, "cost": 1/6, "scope": 1/6,
            "people": 1/6, "dependencies": 1/6, "risks": 1/6
        }
    )
    overdue_age_limit_days: int = 30
    assumption_staleness_days: int = 90
    team_overload_limit: int = 5

    @model_validator(mode="after")
    def weights_sum_to_one(self):
        total = sum(self.weights.values())
        assert abs(total - 1.0) < 1e-6, f"Weights must sum to 1.0, got {total}"
        return self

# ── Scoring output ───────────────────────────────────────

class ContributingFactor(BaseModel):
    dimension: str
    label: str             # e.g. "3 open High-severity risks"
    source_sheet: str
    row_reference: str

class DimensionScores(BaseModel):
    time: float
    cost: float
    scope: float
    people: float
    dependencies: float
    risks: float

class AnalysisResult(BaseModel):
    composite: int                              # 0–100
    rag_status: str                             # On Track / At Risk / Critical
    dimensions: DimensionScores
    contributing_factors: list[ContributingFactor] = []
    executive_summary: str = ""
    recommendations: list[str] = []
    project_name: str = "Unknown"
    generated_at: str = ""                      # ISO timestamp

# ── LLM structured output ────────────────────────────────

class LLMResponse(BaseModel):
    executive_summary: str
    recommendations: list[str] = Field(max_length=3)
```

---

## Key Flows

### Flow 1 — File Upload → Analysis

```
User uploads XLSX
  │
  ▼
app.py: detect file attachment
  │
  ├─► parser.parse(file_path)          → RAMIDData
  │     raises ParseError on bad file
  │
  ├─► config.load_config(project_name) → ThresholdConfig
  │
  ├─► scorer.score(data, config)       → AnalysisResult
  │     (composite, dimensions, factors)
  │
  ├─► llm_client.analyze(data, result) → LLMResponse
  │     (summary, recommendations)
  │     merges into AnalysisResult
  │
  ├─► chart.build_radar(result)        → go.Figure
  │     cl.Plotly(figure) sent to chat
  │
  ├─► report.generate_html(result)     → html string
  │     written to temp file
  │     cl.File sent to chat
  │
  └─► cl.user_session.set("ramid_data", data)
      cl.user_session.set("analysis_result", result)
```

### Flow 2 — Follow-up Q&A

```
User sends text message
  │
  ▼
app.py: check session for analysis_result
  │
  ├─ not found → prompt user to upload file
  │
  └─ found ──► llm_client.answer(
                  question,
                  context=analysis_result,
                  history=conversation_history
               ) → answer string
                   append to conversation_history
                   send as cl.Message
```

### Flow 3 — Config Loading

```
config.load_config(project_name)
  │
  ├─ configs/{project_name}.json exists? → load + validate
  └─ else → load configs/default.json
```

---

## Error Handling

| Scenario | Component | Response |
|---|---|---|
| Non-XLSX file uploaded | parser | `ParseError` → chat error message |
| Missing required column | parser | `ParseError(sheet, column)` → chat error |
| Invalid ThresholdConfig value | config | Pydantic `ValidationError` → chat error with field name |
| LLM API network/auth failure | llm_client | `LLMError` → chat error with failure type |
| LLM response unparseable | llm_client | `LLMError` preserving raw response |
| Missing AnalysisResult fields | report | `ReportError` → chat error with missing fields |
| Any Dimension Score unavailable | chart | chat error, no partial chart rendered |

All errors surface as `cl.Message` with a user-friendly string. Raw exceptions are logged server-side.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: RAMID Parse Round-Trip

*For any* valid RAMID Excel file, parsing it to a `RAMIDData` object, formatting that object to text via `format_for_llm`, then parsing the text back should produce a `RAMIDData` object equivalent to the original.

**Validates: Requirements 1.8**

---

### Property 2: Risk Severity Lookup Correctness

*For any* risk row with a given Probability and Impact, the Severity resolved by the parser must equal the value found at the intersection of that Probability row and Impact column in the Risk Chart sheet.

**Validates: Requirements 1.3**

---

### Property 3: LLM Text Representation Completeness

*For any* `RAMIDData` object, the string produced by `format_for_llm` must contain the key identifiers and counts from each non-empty sheet (risks, issues, milestones, dependencies).

**Validates: Requirements 1.7**

---

### Property 4: Dimension Scores Are In Range

*For any* `RAMIDData` and `ThresholdConfig`, all six dimension scores returned by `scorer.score` must be in the closed interval [0, 100].

**Validates: Requirements 2.1**

---

### Property 5: Composite Score Is Weighted Average

*For any* `DimensionScores` and `ThresholdConfig` whose weights sum to 1.0, the composite score must equal `round(sum(score_i * weight_i for each dimension))`.

**Validates: Requirements 2.8**

---

### Property 6: RAG Classification Matches Thresholds

*For any* composite score value, the RAG status must be exactly "On Track" when score ∈ [75, 100], "At Risk" when score ∈ [50, 74], and "Critical" when score ∈ [0, 49].

**Validates: Requirements 2.9**

---

### Property 7: Scoring Determinism

*For any* `RAMIDData` and `ThresholdConfig`, calling `scorer.score` twice with the same inputs must return identical `AnalysisResult` values.

**Validates: Requirements 2.10**

---

### Property 8: ThresholdConfig Weights Invariant

*For any* `ThresholdConfig`, the sum of all values in `weights` must equal 1.0 (within floating-point tolerance of 1e-6).

**Validates: Requirements 3.1**

---

### Property 9: ThresholdConfig Serialization Round-Trip

*For any* valid `ThresholdConfig`, serializing to JSON and deserializing back must produce an equivalent object with identical field values.

**Validates: Requirements 3.5**

---

### Property 10: Contributing Factors Presence and Ordering

*For any* `AnalysisResult` where `composite < 70`, the `contributing_factors` list must be non-empty (up to 5 items), each factor must contain `dimension`, `label`, `source_sheet`, and `row_reference`, and factors must be ordered by descending impact. When `composite >= 70`, the list must be empty.

**Validates: Requirements 4.1, 4.2, 4.3, 4.6**

---

### Property 11: LLM Response Contains Required Fields

*For any* valid mock LLM API response, the parsed `LLMResponse` must contain a non-empty `executive_summary` and a `recommendations` list with at most 3 items.

**Validates: Requirements 5.2**

---

### Property 12: HTML Report Contains Required Content

*For any* `AnalysisResult`, the HTML string produced by `report.generate_html` must contain the composite score, RAG status, all six dimension score values, the executive summary text, and the project name.

**Validates: Requirements 7.1, 7.3**

---

## Testing Strategy

### Dual Approach

- **Unit tests** — specific examples, edge cases, error conditions (e.g. missing column, invalid config, LLM parse failure).
- **Property tests** — universal properties above, run across many generated inputs.

Both are required. Unit tests catch concrete bugs; property tests verify general correctness.

### Property-Based Testing

Use **Hypothesis** (Python) for all property tests.

Each property test must run a minimum of **100 iterations** (Hypothesis default; increase with `@settings(max_examples=200)` for critical properties).

Tag format in test file comments:
```
# Feature: project-predictive-analyzer, Property N: <property_text>
```

Each correctness property above maps to exactly one property-based test function.

### Unit Test Focus

- `parser.py`: known XLSX fixture → assert correct row counts and severity resolution.
- `scorer.py`: hand-crafted `RAMIDData` → assert expected dimension scores.
- `config.py`: missing file → falls back to default; invalid weight → `ValidationError`.
- `llm_client.py`: mock `openai` client → assert structured output parsing; assert error on bad response.
- `report.py`: known `AnalysisResult` → assert HTML contains required strings.

### Edge Cases to Cover

- Non-XLSX file upload (1.4)
- Missing required column in any sheet (1.5)
- `ThresholdConfig` field out of range (3.4)
- LLM API network failure (5.4)
- LLM response that cannot be parsed (5.3)
- `AnalysisResult` with missing fields passed to report generator (7.5)

---

## Extension Points (Phases 2–4)

These are **not in scope for Phase 1** but the design accommodates them without structural changes:

- **New scoring dimension**: add `_score_X` to `core/scorer.py` and register in `DIMENSION_SCORERS`. No other files change.
- **New data source (SharePoint, Jira, ADO)**: add a new parser module under `core/` that produces `RAMIDData`-compatible rows; plug into `app.py` flow.
- **Risk_Predictor / Assumption_Monitor**: new modules under `core/` that accept `RAMIDData` and return typed results; merged into `AnalysisResult` via optional fields.
- **Portfolio_Engine**: aggregates multiple `AnalysisResult` objects; `AnalysisResult` is already serializable.
- **ML_Engine**: replaces `core/scorer.score` call in `app.py` behind a feature flag; same input/output contract.
- **React frontend (Phase 4)**: add `api/main.py` as a FastAPI wrapper around `core/` — zero changes to `core/`. React calls `api/`, Chainlit calls `core/` directly. Both can coexist.
