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

## Current Implementation Notes

No checked-in interface implementation was found during canonization. This capability is a target requirement from `AGENTS.md`.
