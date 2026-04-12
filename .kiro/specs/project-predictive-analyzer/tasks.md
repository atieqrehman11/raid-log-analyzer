# Implementation Plan: Project Predictive Analyzer

## Overview

UI-first approach: Task 1 delivers a fully runnable Chainlit app with mock data so the interface can be reviewed before any real parsing, scoring, or LLM work begins. Each subsequent task layers in a real component, replacing mock data incrementally.

## Tasks

- [x] 1. UI Shell with Mock Data
  - [x] 1.1 Create `core/models.py` with all Pydantic data models
    - Define `RiskRow`, `IssueRow`, `MilestoneRow`, `DependencyRow`, `AssumptionRow`, `ActionItemRow`, `KPIRow`, `RAMIDData`
    - Define `ThresholdConfig` with `weights_sum_to_one` validator
    - Define `ContributingFactor`, `DimensionScores`, `AnalysisResult`, `LLMResponse`
    - _Requirements: 2.1, 2.8, 2.9, 3.1, 4.2, 5.2_

  - [x] 1.2 Create `mock_data.py` with a hardcoded `AnalysisResult`
    - Composite score 58, RAG "At Risk", all six dimension scores populated
    - Three `ContributingFactor` entries with dimension, label, source_sheet, row_reference
    - Non-empty `executive_summary` and two `recommendations`
    - _Requirements: 2.1, 2.9, 4.1, 4.2, 5.2_

  - [x] 1.3 Create `ui/chart.py` — radar chart builder (no Chainlit imports)
    - Implement `build_radar(result: AnalysisResult) -> go.Figure` using `go.Scatterpolar`
    - Color fill driven by RAG status: green (On Track), amber (At Risk), red (Critical)
    - Raise `ValueError` if any dimension score is missing
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 1.4 Create `templates/report.html` — Jinja2 report template
    - Inline all CSS styles (no external dependencies)
    - Template variables: `result` (AnalysisResult), `project_name`, `generated_at`
    - Include composite score, RAG badge, six dimension scores, summary, recommendations
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 1.5 Create `ui/report.py` — HTML report generator (no Chainlit imports)
    - Implement `generate_html(result: AnalysisResult, project_name: str) -> str`
    - Load and render `templates/report.html` via Jinja2 `Environment`
    - Raise `ReportError` (subclass of `ValueError`) if required fields are missing
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

  - [x] 1.6 Create `app.py` — Chainlit entry point wired to mock data
    - Implement `@cl.on_chat_start` to send a welcome message prompting file upload
    - Implement `@cl.on_message`: on any message, load mock `AnalysisResult` from `mock_data.py`, call `ui.chart.build_radar`, send `cl.Plotly`, call `ui.report.generate_html`, write to temp file, send `cl.File`
    - Store mock result in `cl.user_session` under `analysis_result`
    - _Requirements: 6.1, 7.4, 8.1_

  - [x]* 1.7 Write unit tests for `ui/chart.py` and `ui/report.py` using mock data
    - Test `build_radar` produces a `go.Figure` with six theta labels
    - Test `build_radar` raises on missing dimension score
    - Test `generate_html` output contains composite score, RAG status, project name
    - Test `generate_html` raises `ReportError` on incomplete `AnalysisResult`
    - _Requirements: 6.4, 7.5_

- [ ] 2. Checkpoint — UI review
  - Run `chainlit run app.py`, confirm radar chart and HTML report render correctly with mock data. Ask the user if any UI changes are needed before proceeding.

- [ ] 3. Data Models + RAMID Parser
  - [ ] 3.1 Create `core/config.py` — `ThresholdConfig` loader
    - Implement `load_config(project_name: str) -> ThresholdConfig`
    - Look up `configs/{project_name}.json`; fall back to `configs/default.json`
    - Validate via Pydantic on load; surface `ValidationError` to caller
    - _Requirements: 3.2, 3.3, 3.4_

  - [ ] 3.2 Create `configs/default.json` with equal weights and system defaults
    - Six equal weights (each 1/6), `overdue_age_limit_days: 30`, `assumption_staleness_days: 90`, `team_overload_limit: 5`
    - _Requirements: 3.3_

  - [ ] 3.3 Implement `core/parser.py` — `parse(file_path: str) -> RAMIDData`
    - Load all sheets with `pd.read_excel(path, sheet_name=None)`
    - Map sheets to row models: Risks, Issues, Action Items, Assumptions, Milestones, Dependencies, KPI, Summary
    - Resolve Risk Severity via Risk Chart lookup (Probability × Impact)
    - Raise `ParseError(sheet, column)` on missing required column or non-XLSX input
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [ ] 3.4 Implement `format_for_llm(data: RAMIDData) -> str` in `core/parser.py`
    - Produce a text representation containing key identifiers and counts from each non-empty sheet
    - _Requirements: 1.7_

  - [ ]* 3.5 Write property test for RAMID parse round-trip
    - **Property 1: RAMID Parse Round-Trip**
    - **Validates: Requirements 1.8**

  - [ ]* 3.6 Write property test for Risk Severity lookup correctness
    - **Property 2: Risk Severity Lookup Correctness**
    - **Validates: Requirements 1.3**

  - [ ]* 3.7 Write property test for LLM text representation completeness
    - **Property 3: LLM Text Representation Completeness**
    - **Validates: Requirements 1.7**

  - [ ]* 3.8 Write property tests for `ThresholdConfig`
    - **Property 8: ThresholdConfig Weights Invariant** — Validates: Requirements 3.1
    - **Property 9: ThresholdConfig Serialization Round-Trip** — Validates: Requirements 3.5

  - [ ]* 3.9 Write unit tests for `core/parser.py` and `core/config.py`
    - Known XLSX fixture → assert correct row counts and severity resolution
    - Non-XLSX file → `ParseError`
    - Missing required column → `ParseError` with sheet and column name
    - Missing config file → falls back to default
    - Invalid weight in config → `ValidationError`
    - _Requirements: 1.4, 1.5, 3.4_

- [ ] 4. Scoring Engine
  - [ ] 4.1 Implement `core/scorer.py` — six dimension scorer functions
    - `_score_time(data, config) -> float` from Milestones and KPI data
    - `_score_cost(data, config) -> float` from KPI metrics
    - `_score_scope(data, config) -> float` from Issues and KPI data
    - `_score_people(data, config) -> float` from KPI and Issues data
    - `_score_dependencies(data, config) -> float` weighting Very High overdue/blocked items
    - `_score_risks(data, config) -> float` using Risk Chart severity values
    - Register all six in `DIMENSION_SCORERS` dict
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ] 4.2 Implement `score(data: RAMIDData, config: ThresholdConfig) -> AnalysisResult` in `core/scorer.py`
    - Compute composite as weighted average, cast to `int`
    - Classify RAG status: On Track (75–100), At Risk (50–74), Critical (0–49)
    - Call `_top_factors` and populate `contributing_factors` only when `composite < 70`
    - _Requirements: 2.8, 2.9, 4.1, 4.3, 4.6_

  - [ ] 4.3 Implement `_top_factors(signals, n=5) -> list[ContributingFactor]`
    - Rank by individual impact on composite score, return top `n`
    - Each factor includes `dimension`, `label`, `source_sheet`, `row_reference`
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 4.4 Write property test for dimension scores range
    - **Property 4: Dimension Scores Are In Range**
    - **Validates: Requirements 2.1**

  - [ ]* 4.5 Write property test for composite score formula
    - **Property 5: Composite Score Is Weighted Average**
    - **Validates: Requirements 2.8**

  - [ ]* 4.6 Write property test for RAG classification
    - **Property 6: RAG Classification Matches Thresholds**
    - **Validates: Requirements 2.9**

  - [ ]* 4.7 Write property test for scoring determinism
    - **Property 7: Scoring Determinism**
    - **Validates: Requirements 2.10**

  - [ ]* 4.8 Write property test for contributing factors presence and ordering
    - **Property 10: Contributing Factors Presence and Ordering**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.6**

  - [ ]* 4.9 Write unit tests for `core/scorer.py`
    - Hand-crafted `RAMIDData` → assert expected dimension scores
    - Composite < 70 → contributing_factors non-empty and ordered
    - Composite >= 70 → contributing_factors empty
    - _Requirements: 2.1, 4.1, 4.6_

- [ ] 5. Checkpoint — Scoring validation
  - Ensure all tests pass. Ask the user if scoring weights or RAG thresholds need adjustment before wiring the LLM.

- [ ] 6. LLM Integration + Q&A
  - [ ] 6.1 Implement `core/llm_client.py` — `analyze(data, result) -> LLMResponse`
    - Use `openai.AsyncOpenAI` with `response_format=LLMResponse` (Pydantic structured output)
    - Temperature fixed at 0.2
    - Raise `LLMError` on network/auth failure; preserve raw response on parse failure
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 6.2 Implement `answer(question, context, history) -> str` in `core/llm_client.py`
    - Build prompt from `AnalysisResult` context and `conversation_history`
    - Return plain string answer
    - _Requirements: 8.2, 8.3_

  - [ ] 6.3 Wire full analysis flow in `app.py`
    - On file upload: `parse → load_config → score → llm.analyze → merge LLMResponse into AnalysisResult → build_radar → generate_html`
    - Replace mock data path with real flow; store `ramid_data` and `analysis_result` in session
    - Surface `ParseError`, `LLMError`, `ReportError` as `cl.Message` error strings
    - _Requirements: 1.1, 5.1, 6.1, 7.4, 8.1, 8.4_

  - [ ] 6.4 Wire Q&A flow in `app.py`
    - On text message with no file: check session for `analysis_result`; if absent, prompt upload
    - If present, call `llm_client.answer`, append to `conversation_history`, send as `cl.Message`
    - _Requirements: 8.1, 8.2, 8.3, 8.5_

  - [ ]* 6.5 Write property test for LLM response required fields
    - **Property 11: LLM Response Contains Required Fields**
    - **Validates: Requirements 5.2**

  - [ ]* 6.6 Write unit tests for `core/llm_client.py`
    - Mock `openai` client → assert structured output parsed into `LLMResponse`
    - Mock bad response → `LLMError` with raw response preserved
    - Mock network failure → `LLMError` with failure type
    - _Requirements: 5.3, 5.4_

- [ ] 7. Report correctness tests
  - [ ]* 7.1 Write property test for HTML report content
    - **Property 12: HTML Report Contains Required Content**
    - **Validates: Requirements 7.1, 7.3**

- [ ] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass. Ask the user if questions arise before considering the MVP complete.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Task 1 is fully self-contained — `chainlit run app.py` works with zero real data
- Each task references specific requirements for traceability
- Property tests use Hypothesis with a minimum of 100 examples per property
- Unit tests cover concrete edge cases and error conditions
