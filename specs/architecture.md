# Architecture

## Overview

The target system is a complete prediction platform with scraping-fed data ingestion, treated data persistence, model training, prediction API, and user interface.

## System Context

```mermaid
flowchart LR
    Scraping[Web scraping outputs] --> API[FastAPI API]
    API --> DataPipeline[Data pipeline]
    DataPipeline --> Postgres[(PostgreSQL)]
    API --> ModelPipeline[Model pipeline]
    Postgres --> ModelPipeline
    ModelPipeline --> Artifact[Best model artifact]
    Interface[User interface] --> API
    API --> Artifact
```

## Apps, Services, and Data Stores

| Component | Responsibility | Current Path |
| --- | --- | --- |
| API | Expose ingestion, training, and prediction endpoints | [../sistema/app.py](../sistema/app.py) |
| Data pipeline | Treat raw data and prepare records for training | [../sistema/src/pipeline_dados.py](../sistema/src/pipeline_dados.py) |
| Model pipeline | Benchmark, train, select, and save models | [../sistema/src/pipeline_modelos.py](../sistema/src/pipeline_modelos.py) |
| PostgreSQL | Target treated-data persistence store | Not implemented in checked-in code |
| Interface | Target user-facing application | Not implemented in checked-in code |

## External Systems

- Web scraping sources provide raw real-estate listing data.
- PostgreSQL stores treated property records in the target architecture.

## Dependency Direction

- The API orchestrates pipeline calls and prediction.
- The model pipeline depends on treated data, not raw scraped data.
- Prediction depends on the selected best model artifact.
- The interface depends on the API, not directly on pipelines or storage.

## Runtime and Deployment Context

The checked-in API is a FastAPI app. Current code uses local paths for historical data and model artifacts. The target architecture requires PostgreSQL persistence for treated records.

## Cross-Cutting Technical Rules

<a id="arch-api-001"></a>

### ARCH-API-001: API Workflow Endpoints

**Contract:** The target API exposes `/insertData`, `/trainModels`, and `/predict` for ingestion, training, and prediction.

**Rationale:** These endpoints map to the platform's primary system workflows.

**Traceability:** [CAP-DATA-001](capabilities/data-ingestion.md#cap-data-001), [CAP-MODEL-001](capabilities/model-training.md#cap-model-001), [CAP-PREDICT-001](capabilities/price-prediction.md#cap-predict-001)

<a id="arch-data-001"></a>

### ARCH-DATA-001: PostgreSQL Treated Data Store

**Contract:** Treated records are persisted in PostgreSQL with a saved date for training-window queries.

**Rationale:** Training requires durable, queryable, dated records.

**Traceability:** [CAP-DATA-003](capabilities/data-ingestion.md#cap-data-003), [CAP-MODEL-001](capabilities/model-training.md#cap-model-001)

<a id="arch-model-001"></a>

### ARCH-MODEL-001: Best Model Artifact

**Contract:** The selected best model is persisted as an artifact and loaded by prediction runtime.

**Rationale:** Prediction must use a stable trained model after training completes.

**Traceability:** [CAP-MODEL-003](capabilities/model-training.md#cap-model-003), [CAP-PREDICT-001](capabilities/price-prediction.md#cap-predict-001)

## Persistence and Data Ownership

- PostgreSQL owns treated property records and ingestion dates in the target architecture.
- The model artifact store owns the selected trained model.
- Current local-file persistence is an implementation state, not the final target contract.

## Security and Privacy Architecture

No authentication, authorization, or personal-data policy is specified in current project documentation. This is tracked as a verification and specification gap.

## Decisions and Tradeoffs

- Target storage is PostgreSQL, even though current code uses local files.
- The model pipeline uses only the most recent year of data to prioritize current market relevance.

## Requirement Traceability

| Architecture ID | Requirements |
| --- | --- |
| [ARCH-API-001](#arch-api-001) | [CAP-DATA-001](capabilities/data-ingestion.md#cap-data-001), [CAP-MODEL-001](capabilities/model-training.md#cap-model-001), [CAP-PREDICT-001](capabilities/price-prediction.md#cap-predict-001) |
| [ARCH-DATA-001](#arch-data-001) | [CAP-DATA-003](capabilities/data-ingestion.md#cap-data-003), [CAP-MODEL-001](capabilities/model-training.md#cap-model-001) |
| [ARCH-MODEL-001](#arch-model-001) | [CAP-MODEL-003](capabilities/model-training.md#cap-model-003), [CAP-PREDICT-001](capabilities/price-prediction.md#cap-predict-001) |
