# Requirements Document

## Introduction

The Project Predictive Analyzer is an AI-powered project health engine that ingests RAMID Excel workbooks — containing Risks, Assumptions, Milestones, Issues, and Dependencies data — and produces dimension-based health scores, a radar chart, and natural-language recommendations before problems surface. Users interact through a Chainlit chat interface: they upload the RAMID file in chat, receive an analysis with a radar chart and HTML report, and can then ask follow-up questions about the results.

The requirements are organized by delivery phase: Phase 1 (Hackathon MVP), Phase 2 (Post-Hackathon), Phase 3 (Advanced Forecasting), and Phase 4 (North Star / Enterprise Scale).

---

## Glossary

- **Analyzer**: The core AI-powered project health engine that processes RAMID data and produces scores and insights.
- **RAMID_Parser**: The component responsible for ingesting and parsing RAMID Excel workbooks using pandas and openpyxl.
- **Scoring_Engine**: The component that computes the six radar dimension scores and the Composite Health Score from parsed RAMID signals.
- **LLM_Client**: The component that communicates with the OpenAI API using Pydantic structured outputs to generate summaries and recommendations.
- **Report_Generator**: The component that produces HTML executive summary reports using a Jinja2 template.
- **Chat_UI**: The Chainlit-based chat interface through which users upload files, receive analysis results, and ask follow-up questions.
- **RAMID Workbook**: A structured Excel file containing sheets for Risks, Issues, Action Items, Assumptions, Milestones, Dependencies, KPI, Summary, and Risk Chart.
- **Risk Chart**: The lookup table sheet in the RAMID workbook that maps Probability × Impact to a Severity/Urgency value.
- **Radar Chart**: A Plotly go.Scatterpolar chart visualizing the six health dimensions, rendered as a cl.Plotly element in chat.
- **Composite Health Score**: The weighted average of all six dimension scores, expressed as an integer from 0 to 100.
- **RAG Status**: A Red / Amber / Green classification — On Track (75–100), At Risk (50–74), Critical (0–49).
- **Dimension Score**: A numeric value from 0 to 100 representing health for one of the six radar dimensions: Time, Cost, Scope, People, Dependencies, Risks.
- **Threshold_Config**: A per-project configuration object defining scoring weights and sensitivity parameters, validated via Pydantic BaseModel.
- **Risk_Predictor**: The Phase 2 component that estimates the probability of a risk converting into an issue.
- **Assumption_Monitor**: The Phase 2 component that tracks assumption validity and staleness.
- **SharePoint_Connector**: The Phase 2 component that extracts signals from documents stored in SharePoint.
- **Milestone_Tracker**: The Phase 3 component that forecasts milestone slippage from Milestones sheet data.
- **Dependency_Analyzer**: The Phase 3 component that detects dependency blockages and circular dependencies.
- **Portfolio_Engine**: The Phase 4 component that aggregates health data across Initiative, Account, Region, and Vertical dimensions.
- **ML_Engine**: The Phase 4 machine-learning prediction engine that replaces rule-based scoring once sufficient historical data is available.

---

## Requirements

---

## Phase 1 — Hackathon MVP

---

### Requirement 1: RAMID Workbook Ingestion

**User Story:** As a project manager, I want to upload a RAMID Excel workbook in chat, so that the Analyzer can extract structured project signals without manual data entry.

#### Acceptance Criteria

1. WHEN a user uploads an XLSX file in the Chat_UI, THE RAMID_Parser SHALL parse all sheets using pd.read_excel with sheet_name=None and extract rows into structured records.
2. THE RAMID_Parser SHALL map the following sheets to their corresponding data categories: Risks, Issues, Action Items, Assumptions, Milestones, Dependencies, KPI, Summary, and Risk Chart.
3. THE RAMID_Parser SHALL resolve Severity for each Risk row by looking up Probability × Impact in the Risk Chart sheet.
4. IF the uploaded file is not a valid XLSX format, THEN THE RAMID_Parser SHALL return an error message in chat identifying the invalid format.
5. IF a required column is missing from a sheet, THEN THE RAMID_Parser SHALL return an error in chat identifying the sheet name and missing column.
6. THE RAMID_Parser SHALL produce a structured RAMID object that downstream components can consume without re-reading the file.
7. THE RAMID_Parser SHALL format RAMID objects into a text representation suitable for LLM consumption.
8. FOR ALL valid RAMID Excel files, parsing then formatting then parsing SHALL produce an equivalent RAMID object.

---

### Requirement 2: Dimension-Based Health Scoring

**User Story:** As a project manager, I want a radar chart showing six health dimensions, so that I can see exactly where my project is struggling rather than just a single number.

#### Acceptance Criteria

1. THE Scoring_Engine SHALL compute a Dimension Score (0–100) for each of the six dimensions: Time, Cost, Scope, People, Dependencies, and Risks.
2. THE Scoring_Engine SHALL compute the Time dimension score from Milestones sheet data (At Risk flags, overdue milestones, achieved vs planned ratio) and KPI delivery metrics (missed deadlines, spill-overs).
3. THE Scoring_Engine SHALL compute the Cost dimension score from KPI metrics (revenue on target, margin on target, overtime days, open positions).
4. THE Scoring_Engine SHALL compute the Scope dimension score from Issues sheet data (change request count, new requirements) and KPI metrics (unrealistic expectations flag, new threads opened).
5. THE Scoring_Engine SHALL compute the People dimension score from KPI metrics (turnover, key roles missing, overtime days) and Issues data (performance issues).
6. THE Scoring_Engine SHALL compute the Dependencies dimension score from the Dependencies sheet, weighting Very High importance overdue items and blocked items most heavily.
7. THE Scoring_Engine SHALL compute the Risks dimension score from the Risks sheet, using the Risk Chart severity values to weight open high and very-high severity items.
8. THE Scoring_Engine SHALL compute the Composite Health Score as a weighted average of all six Dimension Scores, expressed as an integer from 0 to 100.
9. THE Scoring_Engine SHALL classify the Composite Health Score as "On Track" (75–100), "At Risk" (50–74), or "Critical" (0–49).
10. WHEN the same RAMID data and Threshold_Config are provided, THE Scoring_Engine SHALL produce the same scores on every invocation.

---

### Requirement 3: Configurable Scoring Thresholds

**User Story:** As a project manager, I want to configure scoring weights and thresholds per project, so that the Scoring_Engine applies context-appropriate sensitivity to my project's signals.

#### Acceptance Criteria

1. THE Threshold_Config SHALL be defined as a Pydantic BaseModel and SHALL include at minimum: dimension weights (six values summing to 1.0), overdue age limit (days), assumption staleness window (days), and team overload limit (count).
2. WHEN a Threshold_Config is provided, THE Scoring_Engine SHALL apply that project's weights and thresholds when computing Dimension Scores.
3. WHERE no Threshold_Config is provided, THE Scoring_Engine SHALL apply equal weights across all six dimensions and system-default threshold values.
4. IF a Threshold_Config value is outside an acceptable range, THEN THE Analyzer SHALL return a validation error in chat identifying the invalid field and its acceptable range.
5. THE Threshold_Config SHALL serialize to and deserialize from JSON without data loss.

---

### Requirement 4: Top-5 Contributing Factors

**User Story:** As a project manager, I want to see the top 5 signals driving my health score down, so that I know exactly what to act on when my project is at risk.

#### Acceptance Criteria

1. WHEN the Composite Health Score is below 70, THE Scoring_Engine SHALL identify and return the top 5 specific RAMID signals that contributed most to the score reduction.
2. Each contributing factor SHALL include: the dimension it belongs to, a short label (e.g. "3 open High-severity risks"), and the source sheet and row reference.
3. THE Scoring_Engine SHALL rank factors by their individual impact on the Composite Health Score, with the highest-impact factor listed first.
4. THE LLM_Client SHALL include the top 5 factors in its structured output response when the score is below 70.
5. THE Chat_UI SHALL display the top 5 factors in the analysis response message with expandable detail for each factor.
6. WHEN the Composite Health Score is 70 or above, THE Scoring_Engine SHALL not return contributing factors.

---

### Requirement 5: LLM-Powered Risk Analysis

**User Story:** As a project manager, I want AI-generated summaries and recommendations, so that I can act on risk signals without interpreting raw data myself.

#### Acceptance Criteria

1. WHEN RAMID data is submitted, THE LLM_Client SHALL send a structured prompt to the OpenAI API and return a response parsed via a Pydantic structured output model.
2. THE LLM_Client SHALL return a response containing: Composite Health Score, RAG Status, all six Dimension Scores, an executive summary, and up to 3 actionable recommendations.
3. IF the LLM API returns a response that cannot be parsed into the expected Pydantic model, THEN THE LLM_Client SHALL return an error that preserves the raw response.
4. IF the LLM API call fails due to a network or authentication error, THEN THE LLM_Client SHALL return an error in chat identifying the failure type.
5. THE LLM_Client SHALL use a temperature setting of 0.2 or lower to ensure consistent outputs.

---

### Requirement 6: Radar Chart Visualization

**User Story:** As a project manager, I want to see a radar chart of my six health dimensions in chat, so that I can visually identify which areas need attention.

#### Acceptance Criteria

1. WHEN analysis is complete, THE Chat_UI SHALL render a Plotly go.Scatterpolar radar chart as a cl.Plotly element inside the chat message.
2. THE Radar Chart SHALL display all six dimension labels (Time, Cost, Scope, People, Dependencies, Risks) with their corresponding Dimension Scores.
3. THE Radar Chart SHALL use a consistent color scheme where the filled area reflects the RAG Status (green for On Track, amber for At Risk, red for Critical).
4. IF any Dimension Score is unavailable, THEN THE Chat_UI SHALL display an error in chat rather than rendering a partial chart.

---

### Requirement 7: Executive Summary HTML Report

**User Story:** As a program manager, I want a formatted HTML report delivered in chat, so that I can share health status with stakeholders without granting system access.

#### Acceptance Criteria

1. WHEN analysis is complete, THE Report_Generator SHALL produce a self-contained HTML file using a Jinja2 template, containing the Composite Health Score, RAG Status, all six Dimension Scores, executive summary, and recommendations.
2. THE Report_Generator SHALL embed all styles inline so the report renders without external CSS dependencies.
3. THE Report_Generator SHALL include the project name and report generation timestamp in the output.
4. THE Chat_UI SHALL deliver the HTML report as a cl.File attachment in the chat thread.
5. IF the analysis result is missing required fields, THEN THE Report_Generator SHALL return an error identifying the missing fields rather than producing a malformed report.

---

### Requirement 8: Conversational Q&A Over Report

**User Story:** As a project manager, I want to ask follow-up questions about my project analysis in chat, so that I can explore specific risks and recommendations without re-uploading the file.

#### Acceptance Criteria

1. WHEN analysis is complete, THE Chat_UI SHALL enter a conversational state where subsequent user messages are treated as questions about the analysis results.
2. WHEN a follow-up question is received, THE LLM_Client SHALL answer using the analysis results and RAMID data from the current session as context.
3. THE Chat_UI SHALL maintain conversation history within the session so that follow-up questions can reference prior answers.
4. WHEN a user uploads a new RAMID file, THE Chat_UI SHALL reset the session context and begin a new analysis.
5. IF no analysis has been performed in the current session, THEN THE Chat_UI SHALL prompt the user to upload a RAMID file before answering project-specific questions.

---

## Phase 2 — Post-Hackathon

---

### Requirement 9: AI Signal Extraction from SharePoint Documents

**User Story:** As a program manager, I want the Analyzer to extract risk signals from SharePoint documents, so that unstructured status updates and meeting notes contribute to health scoring without manual data entry.

#### Acceptance Criteria

1. WHEN a SharePoint site URL and credentials are configured, THE SharePoint_Connector SHALL retrieve documents from the configured document library.
2. WHEN a document is retrieved, THE SharePoint_Connector SHALL extract text content and pass it to the LLM_Client for signal extraction.
3. THE LLM_Client SHALL identify and return risk signals from unstructured document text in the same structured format used for RAMID signals.
4. IF a SharePoint document cannot be retrieved or parsed, THEN THE SharePoint_Connector SHALL log the failure and continue processing remaining documents.
5. WHEN SharePoint signals are incorporated, THE Scoring_Engine SHALL weight them alongside RAMID signals using a configurable blending ratio.

---

### Requirement 10: Risk-to-Issue Conversion Probability

**User Story:** As a project manager, I want to know which risks are likely to become issues, so that I can intervene before escalation occurs.

#### Acceptance Criteria

1. WHEN RAMID data is analyzed, THE Risk_Predictor SHALL compute a conversion probability (0.0–1.0) for each open risk item.
2. WHEN a risk's conversion probability exceeds 0.7, THE Risk_Predictor SHALL flag the risk as "High Escalation Risk" in the analysis output.
3. THE Chat_UI SHALL display the count of high-escalation-risk items in the analysis response message.
4. IF no open risks are present, THEN THE Risk_Predictor SHALL return an empty prediction set rather than an error.

---

### Requirement 11: Issue Escalation Pattern Detection

**User Story:** As a program manager, I want to detect escalation patterns in issues, so that I can identify systemic delivery problems early.

#### Acceptance Criteria

1. WHEN issue data is analyzed, THE Analyzer SHALL compute an aging distribution grouping issues by age bracket: 0–7 days, 8–30 days, 31–90 days, and 90+ days.
2. WHEN a pattern of increasing issue age is detected across consecutive analysis runs, THE Analyzer SHALL flag an escalation pattern in the analysis output.
3. THE Chat_UI SHALL include the aging distribution in the analysis response message.

---

### Requirement 12: Assumption Validity Monitoring

**User Story:** As a project manager, I want to be alerted when assumptions become stale, so that outdated assumptions do not silently undermine project plans.

#### Acceptance Criteria

1. WHEN assumption data is analyzed, THE Assumption_Monitor SHALL identify assumptions whose Validation Due date has passed without a validated date recorded.
2. WHEN stale assumptions are detected, THE Assumption_Monitor SHALL include a staleness alert listing each stale assumption by identifier and age in days.
3. IF an assumption record has no Validation Due date, THEN THE Assumption_Monitor SHALL treat it as stale.
4. THE Chat_UI SHALL surface the staleness alert in the analysis response message when one or more assumptions are stale.

---

### Requirement 13: Action Item Completion Rate and Overload Detection

**User Story:** As a project manager, I want to track action item completion rates and detect team overload, so that I can rebalance workload before burnout affects delivery.

#### Acceptance Criteria

1. THE Analyzer SHALL compute an action item completion rate as the ratio of items with a Date Completed value to total action items, expressed as a percentage.
2. WHEN the number of open action items assigned to a single owner exceeds the configured overload limit, THE Analyzer SHALL flag that owner as overloaded in the analysis output.
3. WHEN the completion rate falls below 50%, THE Scoring_Engine SHALL apply a penalty to the People Dimension Score.
4. THE Chat_UI SHALL include the completion rate and any overloaded owners in the analysis response message.

---

## Phase 3 — Advanced Forecasting

---

### Requirement 14: Milestone Slippage Probability

**User Story:** As a program manager, I want to forecast the probability of milestone slippage, so that I can proactively communicate delivery risk to stakeholders.

#### Acceptance Criteria

1. THE Milestone_Tracker SHALL parse milestone names, phases, due dates, At Risk flags, and statuses from the Milestones sheet.
2. THE Milestone_Tracker SHALL compute a slippage probability (0.0–1.0) for each incomplete milestone based on current RAMID signals and historical patterns.
3. WHEN a milestone's slippage probability exceeds 0.6, THE Milestone_Tracker SHALL include a slippage warning identifying the milestone name and forecast slip duration in days.
4. IF the Milestones sheet cannot be parsed, THEN THE Milestone_Tracker SHALL return an error identifying the failure reason.

---

### Requirement 15: Dependency Blockage Forecast and Circular Dependency Detection

**User Story:** As a program manager, I want to detect blocked and circular dependencies, so that I can resolve structural delivery blockers before they cascade.

#### Acceptance Criteria

1. WHEN dependency data is analyzed, THE Dependency_Analyzer SHALL identify dependencies whose Status is not "Completed" and whose Due Date has passed.
2. THE Dependency_Analyzer SHALL detect circular dependency chains and include each chain as an ordered list of dependency identifiers.
3. WHEN a blocked dependency is detected, THE Dependency_Analyzer SHALL estimate the number of downstream items affected and include this count in the output.
4. IF no dependencies are present, THEN THE Dependency_Analyzer SHALL return an empty result rather than an error.

---

### Requirement 16: Scope Creep Probability and Risk Exposure Trend

**User Story:** As a program manager, I want to detect scope creep and track risk exposure over time, so that I can manage delivery boundaries and communicate trend direction to stakeholders.

#### Acceptance Criteria

1. WHEN consecutive RAMID analysis results are available, THE Analyzer SHALL compute a scope creep probability based on the rate of new issue and risk additions relative to closures.
2. THE Analyzer SHALL compute a risk exposure trend by comparing the total weighted Risks Dimension Score across consecutive analysis runs.
3. WHEN the risk exposure trend increases over 3 or more consecutive runs, THE Analyzer SHALL flag a deteriorating trend in the analysis output.
4. THE Chat_UI SHALL include the scope creep probability and risk exposure trend in the analysis response message.

---

## Phase 4 — North Star / Enterprise Scale

---

### Requirement 17: Portfolio Health Aggregation

**User Story:** As an executive, I want a single pane of glass across all projects, so that I can monitor portfolio health at Initiative, Account, Region, and Vertical dimensions without drilling into individual project reports.

#### Acceptance Criteria

1. THE Portfolio_Engine SHALL aggregate Composite Health Scores across all projects and compute a portfolio-level score for each dimension: Initiative, Account, Region, and Vertical.
2. THE Chat_UI SHALL display portfolio-level health cards for each aggregation dimension alongside individual project health cards.
3. WHEN a portfolio-level score falls below 70, THE Portfolio_Engine SHALL surface the top-contributing projects and their individual scores.
4. THE Portfolio_Engine SHALL support filtering the portfolio view by any combination of Initiative, Account, Region, and Vertical dimensions.

---

### Requirement 18: Live Integration with Jira and Azure DevOps

**User Story:** As a program manager, I want the Analyzer to pull live data from Jira and Azure DevOps, so that health scores reflect real-time delivery signals without manual file uploads.

#### Acceptance Criteria

1. WHEN a Jira project key and API credentials are configured, THE Analyzer SHALL retrieve open issues, epics, and sprint data from the Jira API and incorporate them as RAMID signals.
2. WHEN an Azure DevOps project and API credentials are configured, THE Analyzer SHALL retrieve work items, pipelines, and board data from the Azure DevOps API and incorporate them as RAMID signals.
3. WHEN live data is retrieved, THE Scoring_Engine SHALL recompute the Composite Health Score without requiring a manual file upload.
4. IF a live data source API call fails, THEN THE Analyzer SHALL fall back to the most recently cached data and display a staleness warning in chat indicating the age of the cached data.

---

### Requirement 19: ML-Based Prediction Engine

**User Story:** As a program manager, I want the system to learn from historical project data, so that predictions improve in accuracy over time as more data accumulates.

#### Acceptance Criteria

1. WHEN at least 100 historical project-analysis records are available, THE ML_Engine SHALL train a prediction model to replace the rule-based Scoring_Engine.
2. THE ML_Engine SHALL only deploy a new model version when its accuracy on a held-out validation set exceeds the current model's accuracy.
3. WHEN the ML_Engine is active, THE Chat_UI SHALL indicate that ML-based scoring is in use and display the model's last training date.
4. IF the ML_Engine produces a prediction with confidence below 0.5, THEN THE Analyzer SHALL fall back to the rule-based Scoring_Engine and log the fallback event.
5. THE ML_Engine SHALL serialize trained models to disk and deserialize them on startup without loss of predictive accuracy.
