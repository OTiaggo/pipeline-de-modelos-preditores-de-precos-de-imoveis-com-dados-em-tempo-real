# Data Ingestion and Treatment

## Purpose

Receive raw scraped property data, treat it into the project feature contract, and persist treated records for model training.

## Actors and Permissions

System users can submit raw data. The data pipeline owns cleaning, normalization, and persistence.

## Behavior

<a id="cap-data-001"></a>

### CAP-DATA-001: Raw CSV Ingestion

**Description:** The API shall receive raw property data in CSV format through `/insertData`.

**Priority:** Must

**Rationale:** The platform depends on fresh scraped data for current price prediction.

**Acceptance Criteria:**

1. WHEN a system user submits a valid CSV to `/insertData` THEN the system SHALL load the submitted raw records.
2. WHEN the file cannot be parsed as CSV THEN the system SHALL reject the request with an actionable error.

**Verification:** Automated test

**Traceability:** [DOM-DATA-001](../domain.md#dom-data-001), [ARCH-API-001](../architecture.md#arch-api-001)

<a id="cap-data-002"></a>

### CAP-DATA-002: Feature Treatment

**Description:** The data pipeline shall treat raw property records into the approved feature set and target.

**Priority:** Must

**Rationale:** Model training and prediction require consistent columns and data semantics.

**Acceptance Criteria:**

1. WHEN raw records are processed THEN the output SHALL include the approved model features where available.
2. WHEN records include price data THEN the output SHALL expose the target as `preco`.

**Verification:** Automated test

**Traceability:** [DOM-FEATURES-001](../domain.md#dom-features-001), [CAP-MODEL-001](model-training.md#cap-model-001)

<a id="cap-data-003"></a>

### CAP-DATA-003: Treated Data Persistence

**Description:** Treated records shall be saved in PostgreSQL with the date they were saved.

**Priority:** Must

**Rationale:** The model pipeline must query the last year of treated records for training.

**Acceptance Criteria:**

1. WHEN treated records are accepted THEN the system SHALL persist them in PostgreSQL.
2. WHEN treated records are persisted THEN the system SHALL store an ingestion or saved date.
3. WHEN training data is queried THEN the saved date SHALL support selecting only records from the last year.

**Verification:** Automated integration test

**Traceability:** [DOM-DATA-002](../domain.md#dom-data-002), [ARCH-DATA-001](../architecture.md#arch-data-001), [CAP-MODEL-001](model-training.md#cap-model-001)

<a id="cap-data-004"></a>

### CAP-DATA-004: Ingestion State and Logical Rollback

**Description:** The system shall expose the current treated-data state and the history of uploaded ingestion batches.

**Priority:** Must

**Rationale:** System users need to understand how much active data is available, when it was updated, and whether a bad upload should be excluded.

**Acceptance Criteria:**

1. WHEN a CSV upload is accepted THEN the system SHALL record an ingestion batch with filename, upload date, row counts, status, and error message when applicable.
2. WHEN treated records are saved THEN each record SHALL be associated with the ingestion batch that created it and marked active.
3. WHEN a system user requests the data status THEN the system SHALL return active-record counts, latest upload date, price aggregates, property-type distribution, and top neighborhoods without reprocessing source files.
4. WHEN a system user rolls back an ingestion batch THEN the system SHALL mark the batch and its records inactive without physically deleting the records.
5. WHEN training data is queried THEN inactive records SHALL be excluded.

**Verification:** Automated API test and integration test

**Traceability:** [ARCH-DATA-001](../architecture.md#arch-data-001), [QUAL-RELIABILITY-001](../quality.md#qual-reliability-001)

## Business Rules

- Raw data comes from web scraping sources.
- Treated data is the only input source for model training.

## Out of Scope

- Scraper crawling strategy, source throttling, and anti-bot handling are not specified here.
