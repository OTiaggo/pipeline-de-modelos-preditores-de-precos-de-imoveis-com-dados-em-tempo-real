# Model Training and Selection

## Purpose

Train candidate models with recent treated data and select the best model for prediction.

## Actors and Permissions

System users can trigger training. The model pipeline owns dataset selection, model search, scoring, selection, and model artifact creation.

## Behavior

<a id="cap-model-001"></a>

### CAP-MODEL-001: One-Year Training Window

**Description:** The model pipeline shall train only with treated records from the last year.

**Priority:** Must

**Rationale:** Older market prices should not degrade model relevance.

**Acceptance Criteria:**

1. WHEN `/trainModels` is triggered THEN the system SHALL query treated records saved within the last year.
2. IF treated records older than one year exist THEN the system SHALL exclude them from the training dataset.

**Verification:** Automated integration test

**Traceability:** [CAP-DATA-003](data-ingestion.md#cap-data-003), [DOM-DATA-002](../domain.md#dom-data-002)

<a id="cap-model-002"></a>

### CAP-MODEL-002: Candidate Model Search

**Description:** The model pipeline shall evaluate candidate regression models with grid-search and Bayesian search strategies.

**Priority:** Must

**Rationale:** The platform must choose a strong model instead of relying on a fixed algorithm.

**Acceptance Criteria:**

1. WHEN training runs THEN the system SHALL evaluate regression models from the approved candidate set.
2. WHEN configured for exhaustive search THEN the system SHALL run grid search over candidate hyperparameters.
3. WHEN configured for Bayesian search THEN the system SHALL use Bayesian optimization over candidate hyperparameters.

**Verification:** Automated test and inspection

**Traceability:** [QUAL-MODEL-001](../quality.md#qual-model-001)

<a id="cap-model-003"></a>

### CAP-MODEL-003: Best Model Selection

**Description:** The pipeline shall select the best trained model for production prediction.

**Priority:** Must

**Rationale:** Predictions should use the strongest available model from the training run.

**Acceptance Criteria:**

1. WHEN model evaluation completes THEN the system SHALL compare candidate model metrics.
2. WHEN a best model is selected THEN the system SHALL make that model available to `/predict`.
3. WHEN no model can be trained THEN the system SHALL fail the training request without replacing the existing usable model.

**Verification:** Automated test

**Traceability:** [CAP-PREDICT-001](price-prediction.md#cap-predict-001), [QUAL-RELIABILITY-001](../quality.md#qual-reliability-001)

<a id="cap-model-004"></a>

### CAP-MODEL-004: Training History and Active Model Selection

**Description:** The system shall persist training experiments, individual trained models, metrics, logs, and the active production model selection.

**Priority:** Must

**Rationale:** Operators need auditable model history, metric comparison, long-running training visibility, and a safe way to return to a previous model.

**Acceptance Criteria:**

1. WHEN a training request starts THEN the system SHALL create an experiment with requested models, search strategy, status, start time, and training window.
2. WHEN a model finishes training inside an experiment THEN the system SHALL persist its algorithm, parameters, artifact location, metrics, duration, and champion flag.
3. WHEN an experiment completes successfully THEN the system SHALL activate the experiment champion automatically.
4. WHEN an experiment fails THEN the system SHALL preserve the previously active model.
5. WHEN a system user activates a previously trained model THEN subsequent predictions SHALL use that model.
6. WHEN a system user asks for training status or logs THEN the system SHALL return the persisted experiment state and log lines.

**Verification:** Automated API and model-pipeline tests

**Traceability:** [CAP-MODEL-001](#cap-model-001), [CAP-MODEL-002](#cap-model-002), [CAP-MODEL-003](#cap-model-003), [CAP-PREDICT-001](price-prediction.md#cap-predict-001)

<a id="cap-model-005"></a>

### CAP-MODEL-005: Configurable Training Runs

**Description:** The system shall let system users choose candidate models and either Bayesian search or manual grid parameters for a new training run.

**Priority:** Must

**Rationale:** Operators need control over training cost and model families without editing code.

**Acceptance Criteria:**

1. WHEN a training request names candidate models THEN the system SHALL train only supported requested models.
2. WHEN Bayesian search is requested THEN the system SHALL use the configured number of optimization trials where the candidate supports that strategy.
3. WHEN manual grid search is requested THEN the system SHALL use validated grid parameters supplied for each candidate model.
4. IF the request names an unsupported model or unsupported hyperparameter THEN the system SHALL reject the request before creating a running experiment.

**Verification:** Automated API and model-pipeline tests

**Traceability:** [CAP-MODEL-002](#cap-model-002), [QUAL-MODEL-001](../quality.md#qual-model-001)

## Business Rules

The approved candidate model families are:

- Linear regression
- Neural networks
- SVM
- Multiple linear regression with Ridge or Lasso regularization
- Geographically Weighted Regression
- CatBoost
- LightGBM
- XGBoost
- Random Forest

## Current Implementation Notes

The checked-in `sistema/src/pipeline_modelos.py` currently benchmarks Linear Regression, Random Forest, and XGBoost with `GridSearchCV`, and the training helper saves an XGBoost pipeline. The broader candidate set and Bayesian search are target requirements from `AGENTS.md`.
