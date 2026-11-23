# Pipeline Architecture

## Objective

Turn heterogeneous public procurement sources into a repeatable decision-intelligence workflow.

## Flow

```text
External procurement sources
        |
        v
+---------------------+
| Source adapters     |
| SCMS / Global Fund  |
+---------------------+
        |
        v
data/raw/                 <- ephemeral, gitignored
        |
        | SHA-256 change detection
        v
data/staging/             <- source-shaped but standardized
        |
        v
+---------------------+
| Entity resolution   |
| supplier + product  |
+---------------------+
        |
        v
data/marts/fact_procurement.csv
data/marts/dim_*.csv
        |
        +------------------+
        |                  |
        v                  v
  Quality gates       Signal engine
                         |
                         +--> pricing dispersion
                         +--> supplier HHI
                         +--> commercial value
                         +--> review-priority score
                         |
                         v
                   Alert generation
                         |
                         v
              outputs/ + dashboard
```

## Incremental behavior

Each source download is hashed with SHA-256. The committed source state is compared with the new hash on the next scheduled run.

- unchanged source: existing staged table can be retained
- changed source: source adapter rewrites only that staging table
- marts are rebuilt from the current healthy staging set

This keeps ingestion source-aware without requiring a persistent external orchestrator.

## Failure behavior

Sources are classified as **required** or **optional** in `config/pipeline.json`.

- a required source failure stops the pipeline
- an optional source failure is recorded in `data/state/source_health.json`
- downstream marts continue from healthy staged sources
- quality gates still run before outputs are published

This makes the pipeline observable without pretending an external public endpoint will never fail.

## Data quality gates

The pipeline checks:

- positive prices
- positive quantities
- country completeness
- supplier completeness
- product-key completeness
- duplicate source record IDs

A hard-gate failure prevents signals from being published.

## Signal logic

The review-priority score is intentionally explainable:

- 35% procurement-value percentile
- 35% normalized price-dispersion percentile
- 30% supplier-concentration percentile

It prioritizes review. It does not label procurement as efficient or inefficient.

## Alert rules

The first alert layer flags:

- individual prices at least 40% above the historical median for that product-market combination
- supplier HHI above 0.65
- top supplier share above 75%

Thresholds are configuration, not hard-coded business truth.
