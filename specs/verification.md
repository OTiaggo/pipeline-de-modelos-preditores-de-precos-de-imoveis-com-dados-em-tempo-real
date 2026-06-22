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
| [CAP-DATA-001](capabilities/data-ingestion.md#cap-data-001) | [sistema/tests/test_app.py](../sistema/tests/test_app.py) verifies `/insertData` CSV upload contract with mocked persistence | Automated test | Active |
| [CAP-DATA-002](capabilities/data-ingestion.md#cap-data-002) | [sistema/tests/test_pipeline_dados.py](../sistema/tests/test_pipeline_dados.py) validates notebook-derived treatment, approved features, and `preco` target | Automated test | Active |
| [CAP-DATA-003](capabilities/data-ingestion.md#cap-data-003) | PostgreSQL container, table bootstrap, and application insert code exist; live database integration test is still needed | Automated integration test | Partial |
| [CAP-MODEL-001](capabilities/model-training.md#cap-model-001) | `/trainModels` queries `data_salvamento >= NOW() - INTERVAL '1 year'`; live database integration test is still needed | Automated integration test | Partial |
| [CAP-MODEL-002](capabilities/model-training.md#cap-model-002) | [sistema/tests/test_pipeline_modelos.py](../sistema/tests/test_pipeline_modelos.py) verifies the model registry and grid-search path; full Optuna execution remains integration coverage | Automated test and inspection | Partial |
| [CAP-MODEL-003](capabilities/model-training.md#cap-model-003) | [sistema/tests/test_pipeline_modelos.py](../sistema/tests/test_pipeline_modelos.py) verifies ranking, champion selection, and artifact saving with a reduced registry | Automated test | Active |
| [CAP-PREDICT-001](capabilities/price-prediction.md#cap-predict-001) | [sistema/tests/test_app.py](../sistema/tests/test_app.py) verifies `/predict` returns an estimate with a loaded model | Automated test | Partial |
| [CAP-PREDICT-002](capabilities/price-prediction.md#cap-predict-002) | [sistema/tests/test_app.py](../sistema/tests/test_app.py) verifies the Portuguese prediction payload maps to `MODEL_FEATURES` | Automated test and inspection | Active |
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

Current implementation covers notebook-derived data treatment in [../sistema/src/pipeline_dados.py](../sistema/src/pipeline_dados.py), modular model search and champion artifact saving in [../sistema/src/pipeline_modelos.py](../sistema/src/pipeline_modelos.py), and the target API endpoints `/insertData`, `/trainModels`, and `/predict` in [../sistema/app.py](../sistema/app.py).

## Known Gaps

- PostgreSQL container, table bootstrap, and application write/query code are configured, but live database integration tests are still needed.
- The interface is specified but not present in inspected source.
- Significant price-change detection is specified but not implemented in inspected source.
- Full Optuna integration coverage across all heavy model families is still needed; focused tests use Ridge/Lasso for runtime speed.
- Model-unavailable and prediction-error branches still need automated API tests.

## Accepted Unverified Assumptions

- `AGENTS.md` is treated as the user-approved target product contract for this canonization.
- Current code differences are treated as implementation gaps rather than changes to the target specification.
