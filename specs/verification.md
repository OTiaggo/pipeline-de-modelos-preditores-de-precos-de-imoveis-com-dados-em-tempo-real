# Verification

## Required Checks

- Automated API tests for ingestion, training trigger, model-unavailable prediction, valid prediction, and prediction failure handling.
- Automated data-pipeline tests for feature treatment and dated treated-record persistence.
- Automated model-pipeline tests for one-year training-window filtering, candidate evaluation, metric capture, and best-model selection.
- Integration tests for PostgreSQL persistence once storage is implemented.
- Demonstration or UI tests for the user interface once implemented.

## Requirement-to-Test Matrix

| Requirement ID | Test or Check | Verification Method | Status |
| --- | --- | --- | --- |
| [CAP-DATA-001](capabilities/data-ingestion.md#cap-data-001) | API upload test for `/insertData` CSV parsing and parse failure | Automated test | Gap |
| [CAP-DATA-002](capabilities/data-ingestion.md#cap-data-002) | Data treatment fixture test for approved features and `preco` target | Automated test | Gap |
| [CAP-DATA-003](capabilities/data-ingestion.md#cap-data-003) | PostgreSQL persistence test with saved date | Automated integration test | Gap |
| [CAP-MODEL-001](capabilities/model-training.md#cap-model-001) | Training query excludes records older than one year | Automated integration test | Gap |
| [CAP-MODEL-002](capabilities/model-training.md#cap-model-002) | Candidate model search covers approved configured models and search modes | Automated test and inspection | Gap |
| [CAP-MODEL-003](capabilities/model-training.md#cap-model-003) | Best-model selection and artifact availability test | Automated test | Partial |
| [CAP-PREDICT-001](capabilities/price-prediction.md#cap-predict-001) | `/predict` returns estimate, model-unavailable error, and prediction error | Automated test | Gap |
| [CAP-PREDICT-002](capabilities/price-prediction.md#cap-predict-002) | Prediction schema matches approved feature contract | Automated test and inspection | Gap |
| [CAP-RETRAIN-001](capabilities/retraining-signal.md#cap-retrain-001) | Significant price-change signal and no-signal tests | Automated test and analysis | Gap |
| [CAP-UI-001](capabilities/user-interface.md#cap-ui-001) | Attribute entry and prediction result demo | Demonstration and automated UI test | Gap |
| [QUAL-MODEL-001](quality.md#qual-model-001) | Candidate metric capture inspection | Inspection | Partial |
| [QUAL-RELIABILITY-001](quality.md#qual-reliability-001) | Model-unavailable `/predict` test | Automated test | Gap |
| [QUAL-OBSERVABILITY-001](quality.md#qual-observability-001) | Retraining signal visibility test | Automated test | Gap |
| [QUAL-USABILITY-001](quality.md#qual-usability-001) | Prediction UI flow demo | Demonstration | Gap |

## Manual Verification and Demo Paths

- Upload a valid CSV through the target ingestion endpoint and confirm treated records are persisted with saved dates.
- Trigger model training and confirm only last-year records are used.
- Submit a property prediction request and confirm the returned price comes from the current best model.
- Introduce updated data with significant price movement and confirm the retraining signal is visible.

## Coverage Notes

Current implementation partially covers model benchmarking and model artifact saving in [../sistema/src/pipeline_modelos.py](../sistema/src/pipeline_modelos.py), and prediction request handling in [../sistema/app.py](../sistema/app.py). The API path names currently differ from the target `AGENTS.md` contract: checked-in code exposes `/train`, while the target spec requires `/insertData` and `/trainModels`.

## Known Gaps

- `sistema/src/pipeline_dados.py` is empty in the checked-in source inspected during canonization, while `sistema/app.py` imports data-preparation functions from it.
- PostgreSQL persistence is specified but not implemented in the inspected source.
- The interface is specified but not present in inspected source.
- Significant price-change detection is specified but not implemented in inspected source.
- The full candidate model list and Bayesian search are specified but not implemented in inspected source.
- The full `AGENTS.md` feature contract is not matched by the current API prediction payload.

## Accepted Unverified Assumptions

- `AGENTS.md` is treated as the user-approved target product contract for this canonization.
- Current code differences are treated as implementation gaps rather than changes to the target specification.
