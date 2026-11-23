# Pharmaceutical Procurement Intelligence

A reproducible procurement-intelligence system that ingests public pharmaceutical procurement data, validates and standardizes records, builds analytical marts, and surfaces pricing and supplier-concentration signals for human review.

## What this project demonstrates

This is deliberately more than a one-off analysis.

The system now includes:

- **multi-source ingestion** from historical SCMS procurement data and Global Fund PQR transactions
- **source-level change detection** using SHA-256 hashes
- **raw → staging → canonical marts** data layers
- **supplier entity normalization**
- **hard data-quality gates** before publishing outputs
- **fact and dimension tables** plus an analytical warehouse
- **explainable procurement signal scoring**
- **price and supplier-concentration alerts**
- **automated executive dashboard + review brief**
- **daily GitHub Actions orchestration**
- **unit tests and serialized CI runs** to prevent overlapping pipeline writes

## Current build

The latest full multi-source build processed:

- **9,291 procurement records**
- **2 healthy public data sources**
- **33 markets**
- **122 normalized supplier entities**
- **235 product formulations**
- about **$2.08B in historical procurement value**
- **430 product-market combinations** scored for review

The data are historical and are used to demonstrate procurement-intelligence engineering and analysis. They should not be interpreted as current market prices.

## Architecture

```text
Public procurement sources
        |
        v
+---------------------------+
| Source adapters           |
| SCMS + Global Fund PQR    |
+---------------------------+
        |
        v
data/raw/                   (ephemeral / gitignored)
        |
        | source hashing + freshness state
        v
data/staging/               (source-standardized)
        |
        v
+---------------------------+
| Entity resolution         |
| product + supplier        |
+---------------------------+
        |
        v
+---------------------------+
| Data quality gates        |
| nulls / prices / IDs      |
+---------------------------+
        |
        v
data/marts/
  fact_procurement
  dim_product
  dim_supplier
  dim_market
        |
        v
Analytical warehouse
        |
        +-------------------+
        |                   |
        v                   v
Signal engine           Alert engine
        |                   |
        +---------+---------+
                  |
                  v
        Executive dashboard
        Automated review brief
```

See [docs/architecture.md](docs/architecture.md) for the implementation details.

## Data sources

### 1. SCMS Delivery History Dataset

Historical USAID/PEPFAR health-commodity procurement and shipment data.

The adapter standardizes:

- market
- molecule / formulation
- pack size
- manufacturing supplier
- quantity
- line-item value
- pack price
- delivery dates
- freight and shipment metadata where available

### 2. Global Fund Price & Quality Reporting (PQR)

The pipeline also ingests transaction-level Global Fund procurement data through the public PQR Tableau export.

The current adapter pulls the Kenya transaction view and contributes **749 usable procurement records** to the canonical table.

The source is configured as optional because public Tableau endpoints can change independently of this repository. Source availability is recorded in `data/state/source_health.json`.

## Incremental ingestion

Each source file is hashed after download.

```text
download
  → SHA-256
  → compare with committed source state
  → refresh staging only when source or adapter output changes
```

This keeps raw files ephemeral while preserving pipeline state and reproducibility.

The pipeline also checks staged row counts, so an adapter-code change can refresh staging even when the raw source hash is unchanged.

## Data quality

Before signals are generated, the pipeline checks:

- positive prices
- positive quantities
- country completeness
- supplier completeness
- product-key completeness
- duplicate source record IDs

A hard quality-gate failure stops downstream publication.

The latest successful build passed all hard checks with:

- **100% country completeness**
- **100% supplier completeness**
- **100% product-key completeness**
- **0 duplicate source IDs**

Results are published to `outputs/data_quality_report.json`.

## Canonical data model

The pipeline writes a small star-style analytical model:

- `fact_procurement.csv`
- `dim_product.csv`
- `dim_supplier.csv`
- `dim_market.csv`

Derived marts include:

- `mart_product_market_signals.csv`
- `mart_supplier_summary.csv`
- `mart_country_summary.csv`

An ephemeral SQLite analytical warehouse is rebuilt during each run, with indexed fact tables and views for high-priority signals and large procurement markets.

## Review-priority signal

For product-market combinations with at least five observations:

```text
Review Priority =
    35% procurement-value percentile
  + 35% normalized price-dispersion percentile
  + 30% supplier-concentration percentile
```

Where:

- **procurement value** captures commercial significance
- **price dispersion** is IQR / median pack price
- **supplier concentration** uses a value-weighted HHI

The score is intentionally transparent.

A high score means **investigate this combination further**. It does not mean a purchase was inefficient or overpriced.

## Automated alerts

The first alert layer is configuration-driven.

Current defaults flag:

- transaction prices **40%+ above** the historical product-market median
- supplier HHI above **0.65**
- top supplier share above **75%**

Outputs:

- `outputs/price_alerts.csv`
- `outputs/supplier_concentration_alerts.csv`
- `outputs/alert_summary.json`

Thresholds live in `config/pipeline.json`, rather than being buried inside analysis code.

## Example signals

The multi-source build surfaces combinations such as:

### Abacavir + Lamivudine, Kenya

The Global Fund PQR source pushes this combination to the top of the review queue:

- 22 transactions
- about **$19.1M** historical procurement value
- median pack price **$3.59**
- one recorded manufacturing supplier in this slice
- review-priority score **84.2**

### Zidovudine 300mg, South Africa

- 93 transactions
- 4 manufacturing suppliers
- median pack price **$16.09**
- high historical price dispersion
- top supplier share about **97%**
- review-priority score **83.7**

These are screening signals, not procurement verdicts.

## Automated decision outputs

Every successful pipeline run regenerates:

- executive summary JSON
- product-market signal table
- supplier summary
- country summary
- price alerts
- concentration alerts
- data-quality report
- source-health report
- HTML executive dashboard
- automated Markdown review brief
- charts for markets, suppliers and review priority

## Orchestration

GitHub Actions runs the pipeline:

- on relevant code/config changes
- manually
- **daily**

The CI sequence is:

```text
checkout
→ install
→ unit tests
→ ingestion
→ transformation
→ quality gates
→ marts
→ warehouse
→ signal + alert generation
→ dashboard / brief
→ publish validated outputs
```

A concurrency group prevents multiple pipeline runs from trying to publish generated files simultaneously.

## Run locally

```bash
pip install -r requirements.txt
PYTHONPATH=. python -m src.pipeline.run
```

Run tests:

```bash
PYTHONPATH=. pytest -q
```

## Repository structure

```text
.
├── .github/workflows/
├── config/
│   └── pipeline.json
├── data/
│   ├── staging/
│   ├── state/
│   ├── marts/
│   └── warehouse/
├── docs/
│   └── architecture.md
├── outputs/
│   └── figures/
├── presentation/
├── src/
│   └── pipeline/
│       ├── ingest.py
│       ├── transform.py
│       ├── quality.py
│       ├── signals.py
│       ├── alerts.py
│       ├── warehouse.py
│       ├── publish.py
│       └── run.py
└── tests/
```

## Important caveats

- The underlying procurement datasets are historical.
- Price differences can reflect order size, freight, contract terms, quality requirements, geography, timing, or other legitimate conditions.
- Supplier concentration uses the manufacturing entity/site available in the source data, not necessarily ultimate corporate parent ownership.
- PQR is a public external endpoint and may change schema or availability.
- The system prioritizes review. It does not infer causality or procurement wrongdoing.

## Stack

Python · pandas · NumPy · Matplotlib · SQLite · pytest · GitHub Actions
