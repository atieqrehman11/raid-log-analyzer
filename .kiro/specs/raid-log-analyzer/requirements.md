# Requirements Document

## Introduction

The RAID Log Analyzer is a predictive analytics tool for project managers. It ingests RAID logs stored in XLS/XLSX workbooks (with separate sheets per RAID category) and applies rule-based analytical models to predict project outcomes, identify risks, and surface actionable insights. A future ML-based prediction layer will replace or augment the rule-based engine once sufficient historical data is available.

## Glossary

- **RAID_Log**: An XLS/XLSX workbook containing separate sheets for Risks, Assumptions, Issues, and Dependencies
- **Analyzer**: The core system that ingests, parses, and analyzes RAID log data
- **Parser**: The component responsible for reading and validating XLS/XLSX workbooks into structured data
- **Rule_Engine**: The MVP component that applies configurable rule-based scoring to produce predictions
- **ML_Engine**: The future component that applies trained models to produce predictions (Phase 3)
- **Prediction_Engine**: The abstraction over Rule_Engine and ML_Engine used by the Analyzer
- **Risk_Score**: A numeric value (0–100) representing the aggregate risk exposure of a project
- **Milestone**: A named project checkpoint with a planned completion date, sourced from an external project plan file
- **Action_Item**: A tracked task with an owner, due date, and completion status
- **Dependency**: A relationship where one task or milestone relies on another deliverable
- **Issue**: A confirmed problem currently affecting the project
- **Risk**: A potential future problem with an associated probability and impact
- **Assumption**: A stated condition assumed to be true for planning purposes
- **Report**: A structured HTML or PDF output document summarizing analysis results
- **Snapshot**: A single point-in-time version of a RAID log used for trend comparison

## Prioritization

| # | Requirement | Phase | Rationale |
|---|-------------|-------|-----------|
| 1 | Ingest RAID Log Workbook | Phase 1 | Foundation — nothing works without parsing |
| 2 | Configurable Analysis Thresholds | Phase 1 | Required for usability across different teams |
| 3 | Predict Overall Project Health | Phase 1 | Highest-value output; works from one snapshot |
| 8 | Executive Summary Report Generation (HTML only) | Phase 1 | Primary output artifact; PDF deferred to Phase 2 |
| 4 | Risk-to-Issue Conversion Probability | Phase 2 | High-value prediction; builds on Phase 1 foundation |
| 5 | Issue Escalation Pattern Detection | Phase 2 | Aging and escalation flags; builds on Phase 1 foundation |
| 6 | Assumption Validity Monitoring | Phase 2 | Commonly missed risk signal; builds on Phase 1 foundation |
| 7 | Action Item Completion Rate and Overload Analysis | Phase 2 | Directly actionable; builds on Phase 1 foundation |
| 8 | Executive Summary Report — PDF output | Phase 2 | Adds PDF format to the HTML report from Phase 1 |
| 9 | Ingest External Project Plan | Phase 3 | Requires a second input file; deferred to reduce earlier scope |
| 10 | Predict Milestone Slippage Probability | Phase 3 | Depends on Req 9 |
| 11 | Dependency Blockage Forecast | Phase 3 | Graph/cycle detection adds complexity beyond core loop |
| 12 | Burnout and Overload Risk Detection | Phase 3 | Overload signal already covered by Req 7 |
| 13 | Scope Creep Probability | Phase 3 | Best value with multiple snapshots |
| 14 | Risk Exposure Trend Analysis | Phase 3 | Requires at least two snapshots by definition |

---

## Requirements

### Requirement 1: Ingest RAID Log Workbook

**User Story:** As a project manager, I want to upload my RAID log workbook, so that the system can analyze all RAID categories from a single file without manual data entry.

#### Acceptance Criteria

1. WHEN a valid XLS or XLSX workbook is provided, THE Parser SHALL parse each sheet into its corresponding RAID category model (Risks, Assumptions, Issues, Dependencies)
2. THE Parser SHALL allow the user to configure which sheet name maps to which RAID category
3. THE Parser SHALL support column name variations (e.g., "Risk Description", "Description", "Desc") via a configurable column mapping
4. IF a provided file is not a valid XLS or XLSX format, THEN THE Parser SHALL return a descriptive error message identifying the file and the reason for rejection
5. IF a required column is missing from a sheet, THEN THE Parser SHALL return an error listing the missing columns and the sheet name
6. THE Pretty_Printer SHALL serialize a parsed RAID data model back into a valid XLSX workbook with one sheet per RAID category
7. FOR ALL valid RAID data models, parsing then printing then parsing SHALL produce an equivalent data model (round-trip property)

---

### Requirement 2: Configurable Analysis Thresholds

**User Story:** As a project manager, I want to configure analysis thresholds per project, so that the predictions reflect my team's specific context and norms.

#### Acceptance Criteria

1. THE Analyzer SHALL read threshold configuration from a per-project configuration file
2. THE configuration file SHALL support the following configurable thresholds: issue overdue age (default: 14 days), assumption stale age (default: 30 days), owner overload open item count (default: 5), burnout risk score cutoff (default: 75), and milestone slippage risk score cutoff (default: 60)
3. IF a configuration file is not provided, THEN THE Analyzer SHALL apply all default threshold values and notify the user that defaults are in use
4. IF a configuration file contains an invalid value for a threshold (e.g., a negative number), THEN THE Analyzer SHALL reject the configuration and return a descriptive error identifying the invalid field

---

### Requirement 3: Predict Overall Project Health

**User Story:** As a project manager, I want a prediction of overall project health, so that I can take corrective action before problems become critical.

#### Acceptance Criteria

1. WHEN a RAID log is analyzed, THE Rule_Engine SHALL produce a project health score between 0 and 100
2. WHEN a RAID log is analyzed, THE Rule_Engine SHALL classify the project as one of: "On Track" (score ≥ 70), "At Risk" (score 40–69), or "Critical" (score < 40)
3. THE Rule_Engine SHALL weight open high-severity Risks, unresolved Issues, overdue Action_Items, and invalidated Assumptions in the health score calculation
4. WHEN the health score is below 70, THE Analyzer SHALL surface the top 5 contributing factors driving the score
5. THE Report SHALL display the health score, classification, and contributing factors in a human-readable summary

---

### Requirement 4: Risk-to-Issue Conversion Probability

**User Story:** As a project manager, I want to know which open risks are most likely to materialize into issues, so that I can prioritize mitigation efforts.

#### Acceptance Criteria

1. THE Rule_Engine SHALL calculate a conversion probability score (0–100) for each open Risk based on its probability rating, impact rating, and age in days
2. THE Rule_Engine SHALL flag a Risk as "High Conversion Risk" when its conversion probability score exceeds 70
3. WHEN historical snapshot data is available, THE Rule_Engine SHALL increase the conversion probability score for Risks that have had their probability or impact rating increased across snapshots
4. THE Report SHALL list all High Conversion Risk items ranked by conversion probability score, with their current probability, impact, and age

---

### Requirement 5: Issue Escalation Pattern Detection

**User Story:** As a project manager, I want to identify issues that are escalating in severity or age, so that I can prioritize resolution before they impact delivery.

#### Acceptance Criteria

1. THE Analyzer SHALL identify Issues that have remained open for longer than a configurable threshold (default: 14 days)
2. WHEN an Issue's severity has increased since the previous snapshot, THE Analyzer SHALL flag it as "Escalating"
3. THE Analyzer SHALL compute an issue aging distribution showing the count of open Issues grouped by age ranges: 0–7 days, 8–14 days, 15–30 days, and 30+ days
4. THE Report SHALL list all Escalating Issues with their current severity, age in days, and assigned owner

---

### Requirement 6: Assumption Validity Monitoring

**User Story:** As a project manager, I want to track assumptions that may have been invalidated, so that I can update my project plan before invalid assumptions cause problems.

#### Acceptance Criteria

1. THE Analyzer SHALL identify Assumptions that have not been reviewed within a configurable threshold (default: 30 days)
2. WHEN an Assumption is marked as invalidated in the RAID log, THE Analyzer SHALL flag it and link it to any related Risks or Issues
3. THE Report SHALL list all stale and invalidated Assumptions with their last review date and associated items
4. THE Analyzer SHALL include the ratio of invalidated Assumptions to total Assumptions as a factor in the project health score calculation

---

### Requirement 7: Action Item Completion Rate and Overload Analysis

**User Story:** As a project manager, I want to track action item completion rates and identify overloaded team members, so that I can assess accountability and redistribute work before burnout occurs.

#### Acceptance Criteria

1. THE Analyzer SHALL calculate the overall action item completion rate as the percentage of Action_Items marked complete out of total Action_Items
2. THE Analyzer SHALL calculate per-owner completion rates and open item counts for all owners with two or more assigned Action_Items
3. WHEN an Action_Item is past its due date and not marked complete, THE Analyzer SHALL flag it as "Overdue"
4. THE Rule_Engine SHALL flag an owner as "Overloaded" when the owner has more than a configurable number of open Action_Items (default: 5) simultaneously
5. THE Rule_Engine SHALL project the expected completion date for all open Action_Items based on the current per-owner completion velocity
6. THE Report SHALL include overall completion rate, per-owner rates, overdue item count, overloaded owners, and projected completion dates

---

### Requirement 8: Executive Summary Report Generation

**User Story:** As a project manager, I want to generate a concise executive summary, so that I can share project health status with stakeholders without exposing raw log data.

#### Acceptance Criteria

1. WHEN analysis is complete, THE Analyzer SHALL generate an executive summary Report in HTML format (Phase 1); PDF format SHALL be added in Phase 2
2. THE Report SHALL include: project health score and classification, top 3 risks by conversion probability, overdue action item count, burnout risk owners, scope creep indicator, and key recommendations
3. THE Report SHALL be generated within 30 seconds of analysis completion for RAID logs containing up to 500 rows
4. WHERE a company logo or project name is configured, THE Report SHALL include it in the report header
5. THE Report SHALL include a section clearly labeling all predictions as rule-based estimates and not guarantees

---

### Requirement 9: Ingest External Project Plan

**User Story:** As a project manager, I want to provide a separate project plan file containing milestone dates, so that the system can correlate RAID items with schedule data.

#### Acceptance Criteria

1. WHEN an external project plan file is provided in XLS or XLSX format, THE Parser SHALL extract Milestone names and planned completion dates
2. THE Analyzer SHALL link RAID items to Milestones by matching milestone name references in the RAID log
3. IF no external project plan is provided, THEN THE Analyzer SHALL perform all analyses that do not require milestone data and notify the user that milestone-dependent analyses are unavailable
4. IF a referenced Milestone name in the RAID log does not exist in the project plan, THEN THE Analyzer SHALL report the unresolved reference to the user

---

### Requirement 10: Predict Milestone Slippage Probability

**User Story:** As a project manager, I want to know which milestones are at risk of slipping and by how much, so that I can reallocate resources or adjust the schedule proactively.

#### Acceptance Criteria

1. WHEN milestone data is available, THE Rule_Engine SHALL calculate a slippage probability score (0–100) for each Milestone
2. THE Rule_Engine SHALL consider open Dependencies, unresolved Issues linked to a Milestone, and overdue Action_Items when calculating slippage probability
3. THE Rule_Engine SHALL flag a Milestone as "At Risk" when its slippage probability score exceeds 60
4. WHEN a Milestone is flagged "At Risk", THE Report SHALL include the estimated delay range in days and the top contributing factors
5. IF no milestone data is present, THEN THE Analyzer SHALL notify the user that milestone slippage analysis is unavailable

---

### Requirement 11: Dependency Blockage Forecast

**User Story:** As a project manager, I want to forecast which dependencies are likely to become blockers, so that I can address them before they cascade into schedule delays.

#### Acceptance Criteria

1. THE Analyzer SHALL build a dependency graph from the Dependencies sheet of the RAID log
2. THE Analyzer SHALL identify nodes with three or more incoming dependencies and flag them as "Bottlenecks"
3. THE Rule_Engine SHALL assign a blockage risk score to each Dependency based on the status of its upstream items and the number of downstream items it blocks
4. WHEN a Dependency is forecast as a likely blocker, THE Report SHALL list the item, its blockage risk score, and the items it would block
5. IF the dependency data contains a circular dependency, THEN THE Analyzer SHALL detect it and report the cycle to the user

---

### Requirement 12: Burnout and Overload Risk Detection

**User Story:** As a project manager, I want to identify team members at risk of burnout, so that I can intervene before it affects delivery quality or causes attrition.

#### Acceptance Criteria

1. THE Rule_Engine SHALL compute an overload risk score for each owner based on the count of open Action_Items, count of open Issues assigned to them, and the ratio of overdue items to total assigned items
2. THE Rule_Engine SHALL flag an owner as "Burnout Risk" when their overload risk score exceeds a configurable threshold (default: 75)
3. THE Report SHALL list all Burnout Risk owners with their overload risk score, open item count, and overdue item ratio
4. WHEN an owner is flagged as Burnout Risk, THE Report SHALL recommend redistributing their highest-priority open items

---

### Requirement 13: Scope Creep Probability

**User Story:** As a project manager, I want to detect signs of scope creep, so that I can manage stakeholder expectations and protect the project schedule.

#### Acceptance Criteria

1. WHEN RAID log snapshots from multiple time periods are provided, THE Analyzer SHALL track the rate of new Risk and Issue additions per snapshot period
2. THE Rule_Engine SHALL calculate a scope creep probability score based on the rate of new item additions, the ratio of new items to resolved items, and the presence of Assumptions marked as invalidated
3. THE Rule_Engine SHALL flag the project as "Scope Creep Likely" when the scope creep probability score exceeds 65
4. THE Report SHALL include the scope creep probability score and the primary indicators contributing to it
5. WHILE only a single RAID log snapshot is available, THE Analyzer SHALL compute a static scope creep indicator based on the current ratio of open items to resolved items

---

### Requirement 14: Risk Exposure Trend Analysis

**User Story:** As a project manager, I want to see how my project's risk exposure changes over time, so that I can evaluate whether my risk mitigation efforts are working.

#### Acceptance Criteria

1. WHEN RAID log snapshots from multiple time periods are provided, THE Analyzer SHALL compute a Risk_Score for each period and present them as a chronological trend
2. THE Analyzer SHALL identify periods where Risk_Score increased by more than 15 points between consecutive snapshots and flag them as "Risk Spikes"
3. WHEN a Risk Spike is detected, THE Report SHALL include the risks that were added or escalated during that period
4. WHILE trend data contains fewer than two snapshots, THE Analyzer SHALL notify the user that trend analysis requires at least two RAID log snapshots
