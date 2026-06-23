# Price Prediction

## Purpose

Estimate a property price from user-provided property attributes using the best trained model.

## Actors and Permissions

End users submit property attributes through the interface or API. The API owns request validation and prediction response formatting.

## Behavior

<a id="cap-predict-001"></a>

### CAP-PREDICT-001: Predict Property Price

**Description:** The API shall receive property attributes and return an estimated price from the best trained model.

**Priority:** Must

**Rationale:** This is the primary user-facing value of the platform.

**Acceptance Criteria:**

1. WHEN a user submits valid property attributes to `/predict` THEN the system SHALL return an estimated price.
2. WHEN no trained model is available THEN the system SHALL reject the request with a model-unavailable error.
3. WHEN prediction fails THEN the system SHALL return an error instead of a misleading price.

**Verification:** Automated test

**Traceability:** [CAP-MODEL-003](model-training.md#cap-model-003), [DOM-FEATURES-001](../domain.md#dom-features-001)

<a id="cap-predict-002"></a>

### CAP-PREDICT-002: Prediction Feature Contract

**Description:** Prediction input shall support the approved property features needed by the trained model.

**Priority:** Must

**Rationale:** User-entered attributes must align with training semantics.

**Acceptance Criteria:**

1. WHEN a user submits a prediction request THEN the payload SHALL include required model features.
2. WHEN optional features are absent THEN the system SHALL use documented defaults or reject the request if no valid default exists.

**Verification:** Automated test and inspection

**Traceability:** [DOM-FEATURES-001](../domain.md#dom-features-001), [CAP-UI-001](user-interface.md#cap-ui-001)

## Examples

The target feature vocabulary includes neighborhood, area, bedrooms, bathrooms, suites, floor, parking spaces, amenities, and standardized property type.

## Current Implementation Notes

The checked-in API currently exposes `/predict` with a smaller payload using area, bedrooms, bathrooms, parking spaces, neighborhood, latitude, longitude, and created date. The full `AGENTS.md` feature contract remains a target requirement.
