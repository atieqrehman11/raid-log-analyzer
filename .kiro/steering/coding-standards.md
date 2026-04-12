---
inclusion: always
---

# Coding Standards — Project Predictive Analyzer

## Project Structure Rule (Non-Negotiable)

- `core/` — zero unused imports. Pure Python business logic only.
- `ui/` — zero unused imports. Rendering helpers only (chart, report).
- `app.py` — only file that imports `chainlit`. Orchestrates UI flow.
- `tests/` — all tests live here. No test code in source modules.
- `api/` — FastAPI layer. Wraps `core/` only.

---

## Backend (`core/`)

### General
- All public functions must have type annotations on parameters and return types.
- All public functions must have a one-line docstring.
- Raise specific custom exceptions (`ParseError`, `LLMError`, `ReportError`) — never raise bare `Exception`.
- Never swallow exceptions silently. Log and re-raise or convert to typed error.
- No `print()` statements — use Python `logging` module.

### Data Models (`core/models.py`)
- All data models use Pydantic `BaseModel`.
- All fields must have explicit types. No untyped `dict` or `Any` fields.
- Optional fields must default to `None` or a sensible default — never leave them required when they can be absent.
- Validators use `@model_validator(mode="after")` — not deprecated `@validator`.

### Scoring (`core/scorer.py`)
- Each dimension scorer is a private function `_score_<dimension>(data, config) -> float`.
- All dimension scorers are registered in `DIMENSION_SCORERS` dict — never called directly from `score()`.
- Scores must always be clamped to `[0.0, 100.0]` before returning.
- `score()` must be deterministic — same inputs always produce same outputs.

### Parser (`core/parser.py`)
- Use `pd.read_excel(path, sheet_name=None)` — load all sheets in one call.
- Sheet name matching must be case-insensitive.
- Missing required columns raise `ParseError(sheet=..., column=...)` with both fields populated.
- Date columns must be parsed with `errors="coerce"` — never crash on bad dates.

### LLM Client (`core/llm_client.py`)
- Temperature must be `0.2` or lower — never higher.
- Always use Pydantic structured outputs (`response_format=ModelClass`).
- Network/auth failures raise `LLMError` with `failure_type` field.
- Unparseable responses raise `LLMError` with `raw_response` field preserved.
- All LLM calls are `async`.

---

## UI Layer (`ui/` and `app.py`)

### `ui/chart.py` and `ui/report.py`
- No `import chainlit` — ever.
- Functions return plain Python objects (`go.Figure`, `str`) — caller decides how to send.
- Raise `ValueError` or typed errors on bad input — never return `None` silently.

### `app.py` (Chainlit)
- Session state stored only via `cl.user_session.set/get` — no module-level globals.
- Each logical output (summary, chart, file) sent as a separate `cl.Message` — do not mix `cl.Plotly` and `cl.File` in the same `elements` list (Chainlit 2.x bug).
- All errors caught and surfaced as `cl.Message` with user-friendly text — never let raw exceptions reach the UI.
- File elements use `cl.File(name=..., path=...)` — no `display="inline"` on HTML files.

---

## Error Handling

- Custom exceptions live in `core/models.py` or alongside the module that raises them.
- Every `except` block must either re-raise, log, or convert to a typed error — no bare `except: pass`.
- User-facing error messages must be plain English — no stack traces, no internal field names.

---

## Testing

- Property-based tests use `hypothesis` — minimum 100 examples per property.
- Unit tests use `pytest` — one test file per source module.
- Test files named `test_<module>.py` in `tests/`.
- Mock external calls (`openai`, file I/O) — tests must run offline.
- No test should modify files outside of `tmp/` or `tempfile` locations.

---

## Git & Commits
- Dont commit anything until it is asked to do so.
- Commit messages: `<type>: <short description>` — e.g. `feat: add risk scorer`, `fix: null template in chart`.
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
- Never commit `.env`, `venv/`, `__pycache__/`, or `*.pyc`.
- `.gitignore` must include: `.env`, `venv/`, `__pycache__/`, `*.pyc`, `tmp/`, `*.html` (generated reports).

---

## Dependencies

- All dependencies pinned in `requirements.txt` with minimum versions.
- No new dependency added without updating `requirements.txt`.
- Dev-only dependencies (pytest, hypothesis) kept separate from runtime deps if a `requirements-dev.txt` is added.
