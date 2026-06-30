# User Interface

## Purpose

Provide a user-facing way to interact with prediction, training, and retraining workflows.

## Actors and Permissions

End users enter property attributes for prediction. System users interact with data upload, training, and retraining indicators.

## Behavior

<a id="cap-ui-001"></a>

### CAP-UI-001: Property Attribute Entry

**Description:** The interface shall let a user enter property attributes and view the estimated price from the best trained model.

**Priority:** Must

**Rationale:** Non-technical users need a practical way to use the prediction platform.

**Acceptance Criteria:**

1. WHEN a user opens the interface THEN they SHALL be able to enter property attributes from the prediction feature contract.
2. WHEN prediction succeeds THEN the interface SHALL show the estimated property price.
3. WHEN prediction fails THEN the interface SHALL show a clear failure state.

**Verification:** Demonstration and automated UI test

**Traceability:** [CAP-PREDICT-001](price-prediction.md#cap-predict-001), [CAP-PREDICT-002](price-prediction.md#cap-predict-002), [QUAL-USABILITY-001](../quality.md#qual-usability-001)

<a id="cap-ui-002"></a>

### CAP-UI-002: Data Operations Dashboard

**Description:** The interface shall show active data state, ingestion history, upload results, and logical rollback controls.

**Priority:** Must

**Rationale:** System users need to manage scraping uploads and understand the available dataset before training.

**Acceptance Criteria:**

1. WHEN a system user opens the data page THEN the interface SHALL show active record totals, latest upload, price aggregates, property-type distribution, and top neighborhoods.
2. WHEN ingestion history exists THEN the interface SHALL show batch status and row counts.
3. WHEN a system user rolls back a batch THEN the interface SHALL ask for confirmation and refresh the data state after success.

**Verification:** Demonstration and automated UI test

**Traceability:** [CAP-DATA-004](data-ingestion.md#cap-data-004), [QUAL-USABILITY-001](../quality.md#qual-usability-001)

<a id="cap-ui-003"></a>

### CAP-UI-003: Model Operations Dashboard

**Description:** The interface shall show model history, metrics, active model details, training configuration, training logs, drift state, and model activation controls.

**Priority:** Must

**Rationale:** System users need to monitor model health and safely manage retraining.

**Acceptance Criteria:**

1. WHEN a system user opens the model page THEN the interface SHALL show the active model, leaderboard, experiment history, drift status, and feature importance when available.
2. WHEN a system user starts a new training run THEN the interface SHALL let them choose model families, search strategy, trial count, and manual grids as JSON.
3. WHEN training is running THEN the interface SHALL poll and display experiment logs/status.
4. WHEN a previous model exists THEN the interface SHALL offer an activation action.

**Verification:** Demonstration and automated UI test

**Traceability:** [CAP-MODEL-004](model-training.md#cap-model-004), [CAP-MODEL-005](model-training.md#cap-model-005), [CAP-RETRAIN-001](retraining-signal.md#cap-retrain-001), [QUAL-OBSERVABILITY-001](../quality.md#qual-observability-001)

## Current Implementation Notes

No checked-in interface implementation was found during canonization. This capability is a target requirement from `AGENTS.md`.
