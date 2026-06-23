# Retraining Signal

## Purpose

Identify significant price changes and signal when the system should be retrained with updated data.

## Actors and Permissions

The data and model pipelines own price-change detection. System users consume the retraining signal and can trigger retraining.

## Behavior

<a id="cap-retrain-001"></a>

### CAP-RETRAIN-001: Significant Price Change Signal

**Description:** The system shall identify significant price changes in updated data and signal that model retraining is needed.

**Priority:** Must

**Rationale:** Market shifts can reduce model accuracy before a user manually notices degradation.

**Acceptance Criteria:**

1. WHEN newly treated data indicates significant price change THEN the system SHALL signal the need for retraining.
2. WHEN no significant price change is detected THEN the system SHALL avoid signaling unnecessary retraining.
3. WHEN the signal cannot be computed THEN the system SHALL expose the failure as an operational gap instead of silently ignoring it.

**Verification:** Automated test and analysis

**Traceability:** [CAP-DATA-003](data-ingestion.md#cap-data-003), [CAP-MODEL-001](model-training.md#cap-model-001), [QUAL-OBSERVABILITY-001](../quality.md#qual-observability-001)

## Business Rules

- The significance threshold is not yet specified in source documentation and must be defined before implementation can be complete.

## Out of Scope

- Automatic retraining without user intent is not required by the current project description.
