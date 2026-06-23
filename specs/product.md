# Product

## Purpose

This project is a complete real-estate price prediction platform for Fortaleza, Ceara. It uses up-to-date scraped listing data to train, retrain, and serve models that estimate property prices from user-provided property attributes.

## Users, Actors, and Stakeholders

| Actor | Role |
| --- | --- |
| End user | Enters property attributes and receives an estimated price. |
| System user | Uploads or triggers new data ingestion and model retraining. |
| Data pipeline | Cleans raw listing data and persists treated records. |
| Model pipeline | Trains candidate models and selects the best model for prediction. |
| API | Exposes ingestion, training, and prediction workflows. |
| Interface | Provides a user-facing way to interact with prediction and retraining workflows. |

## Business Goals

- Predict real-estate sale prices for properties in Fortaleza using recent market data.
- Keep model training aligned with current market behavior by using data from the last year.
- Let users trigger retraining when desired.
- Detect significant price changes and signal when retraining is needed.
- Provide a complete platform composed of data pipeline, model pipeline, API, and interface.

## Capability Map

| Capability | Spec | Primary Actors | Status |
| --- | --- | --- | --- |
| Data Ingestion and Treatment | [capabilities/data-ingestion.md](capabilities/data-ingestion.md) | System user, Data pipeline | Target |
| Model Training and Selection | [capabilities/model-training.md](capabilities/model-training.md) | System user, Model pipeline | Target |
| Price Prediction | [capabilities/price-prediction.md](capabilities/price-prediction.md) | End user, API, Interface | Target |
| Retraining Signal | [capabilities/retraining-signal.md](capabilities/retraining-signal.md) | Data pipeline, Model pipeline, System user | Target |
| User Interface | [capabilities/user-interface.md](capabilities/user-interface.md) | End user, System user | Target |

## Core User Journeys

1. A system user uploads raw CSV listing data through the API.
2. The data pipeline treats the raw data and persists treated records with an ingestion date.
3. A system user triggers model training.
4. The model pipeline loads treated records from the last year, runs model search, and selects the best model.
5. An end user enters property attributes in the interface.
6. The API predicts the property price with the best trained model and returns the estimate.

## Business Concepts

- Property listing
- Raw scraped data
- Treated property record
- Training window
- Candidate model
- Best model
- Price-change signal

## Boundaries and Out of Scope

- The canonical product target is Fortaleza/Ceara real estate price prediction.
- Historical data older than one year is out of scope for model training unless a future requirement changes the training window.
- Real-time scraping implementation details are out of scope for these core specs except where they affect ingestion contracts.

## Assumptions, Constraints, and Dependencies

- Raw data is obtained through web scraping.
- Treated data is intended to be stored in PostgreSQL.
- Current code implements part of the API and model workflow with local files; PostgreSQL persistence, the documented `/insertData` and `/trainModels` paths, and the user interface remain verification gaps.

## Glossary

| Term | Meaning |
| --- | --- |
| Alvo | The prediction target, `preco`. |
| Feature | A property attribute used by the model. |
| Retreino | A new model training run using updated treated data. |
| Dados tratados | Cleaned and standardized records ready for storage and model training. |
