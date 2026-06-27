# Domain

## Glossary and Ubiquitous Language

| Term | Meaning |
| --- | --- |
| Imovel | A real-estate property in Fortaleza/Ceara. |
| Dados brutos | Scraped listing data before treatment. |
| Dados tratados | Cleaned records ready for persistence and model training. |
| Feature | Property attribute used by the prediction model. |
| Preco | The target value predicted by the model. |
| Modelo campeao | The best selected model available for prediction. |
| Retreino | A new training run with updated treated data. |

## Core Concepts

| Concept | Meaning | Detail Spec |
| --- | --- | --- |
| Property feature set | Approved model input attributes | This file |
| Training window | Last-year slice of treated data | This file |
| Model artifact | Persisted trained model used by prediction | This file |

## Entities and Relationships

```mermaid
flowchart TD
    Raw[Dados brutos de scraping] --> Treated[Dados tratados]
    Treated --> Store[(PostgreSQL)]
    Store --> Training[Pipeline de modelos]
    Training --> Model[Modelo campeao]
    UserInput[Atributos do imovel] --> Predict[/predict]
    Model --> Predict
    Predict --> Price[Preco estimado]
```

## Cross-Cutting Invariants

<a id="dom-data-001"></a>

### DOM-DATA-001: Raw Data Origin

**Invariant:** Raw data used by the platform originates from web scraping sources.

**Applies To:** Data ingestion, model training, retraining signal.

**Traceability:** [CAP-DATA-001](capabilities/data-ingestion.md#cap-data-001)

<a id="dom-data-002"></a>

### DOM-DATA-002: Dated Treated Records

**Invariant:** Treated records intended for training must carry a saved or ingestion date that supports selecting the last year of data.

**Applies To:** Data ingestion, model training, PostgreSQL persistence.

**Traceability:** [CAP-DATA-003](capabilities/data-ingestion.md#cap-data-003), [CAP-MODEL-001](capabilities/model-training.md#cap-model-001)

<a id="dom-features-001"></a>

### DOM-FEATURES-001: Approved Prediction Feature Set

**Invariant:** Training and prediction must use a consistent feature vocabulary.

**Applies To:** Data treatment, model training, prediction, interface.

**Traceability:** [CAP-DATA-002](capabilities/data-ingestion.md#cap-data-002), [CAP-PREDICT-002](capabilities/price-prediction.md#cap-predict-002)

## Data Semantics

The approved target is:

- `preco`

The approved features from `AGENTS.md` are:

- `bairro`
- `area_m2`
- `quartos`
- `banheiros`
- `suites`
- `andar`
- `vagas`
- `portaria`
- `vista_mar`
- `condominio_fechado`
- `piscina`
- `deck`
- `varanda`
- `academia`
- `salao_festa`
- `salao_jogos`
- `quadra_campo`
- `tipo_imovel_padronizado`

The repository README also mentions address, latitude, longitude, state, and number as scraping fields. These are source-observed data fields, but they are not part of the approved `AGENTS.md` model feature set unless promoted by a future requirement.

## Requirement Traceability

| Domain ID | Requirements |
| --- | --- |
| [DOM-DATA-001](#dom-data-001) | [CAP-DATA-001](capabilities/data-ingestion.md#cap-data-001) |
| [DOM-DATA-002](#dom-data-002) | [CAP-DATA-003](capabilities/data-ingestion.md#cap-data-003), [CAP-MODEL-001](capabilities/model-training.md#cap-model-001) |
| [DOM-FEATURES-001](#dom-features-001) | [CAP-DATA-002](capabilities/data-ingestion.md#cap-data-002), [CAP-PREDICT-002](capabilities/price-prediction.md#cap-predict-002) |
