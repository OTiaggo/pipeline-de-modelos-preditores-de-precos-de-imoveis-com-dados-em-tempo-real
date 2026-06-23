# Quality

<a id="qual-model-001"></a>

## QUAL-MODEL-001: Comparative Model Quality

**Quality Attribute:** Functional suitability

**Description:** Training must compare candidate models with objective metrics before selecting the best model.

**Business Impact:** Users depend on the selected model for credible property price estimates.

**Metric:** At minimum, each candidate training run records a comparable regression metric such as R2, MAE, or RMSE.

**Priority:** Must

**Verification:** Automated test and inspection

**Constraints:** Metric choice and selection threshold may be refined by future requirements.

**Traceability:** [CAP-MODEL-002](capabilities/model-training.md#cap-model-002), [CAP-MODEL-003](capabilities/model-training.md#cap-model-003)

<a id="qual-reliability-001"></a>

## QUAL-RELIABILITY-001: Prediction Availability Guard

**Quality Attribute:** Reliability

**Description:** Prediction must not return an estimate when no trained model is available.

**Business Impact:** A clear unavailable response is safer than a fabricated or stale prediction.

**Metric:** `/predict` returns a model-unavailable error when no model is loaded.

**Priority:** Must

**Verification:** Automated test

**Constraints:** Future work should define model freshness and stale-model behavior.

**Traceability:** [CAP-PREDICT-001](capabilities/price-prediction.md#cap-predict-001)

<a id="qual-observability-001"></a>

## QUAL-OBSERVABILITY-001: Retraining Signal Visibility

**Quality Attribute:** Observability

**Description:** The system must expose significant price-change detection outcomes or failures.

**Business Impact:** Users need to know when updated data suggests retraining.

**Metric:** Each significant-change evaluation produces a visible signal, no-signal result, or failure state.

**Priority:** Must

**Verification:** Automated test and demonstration

**Constraints:** The significant-change threshold is not yet specified.

**Traceability:** [CAP-RETRAIN-001](capabilities/retraining-signal.md#cap-retrain-001)

<a id="qual-usability-001"></a>

## QUAL-USABILITY-001: Prediction Interaction Clarity

**Quality Attribute:** Usability

**Description:** The interface must make prediction input, success, and failure states clear to users.

**Business Impact:** Users should be able to obtain and understand a property price estimate without API knowledge.

**Metric:** A user can submit property attributes and distinguish success from validation or prediction failure in a manual demo.

**Priority:** Must

**Verification:** Demonstration and automated UI test

**Constraints:** No interface implementation is currently checked in.

**Traceability:** [CAP-UI-001](capabilities/user-interface.md#cap-ui-001)
