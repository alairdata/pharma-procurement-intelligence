# Pharmaceutical Procurement Intelligence

A compact, reproducible analytics project that turns public global-health procurement data into decision signals around pricing variation, supplier concentration, market exposure, and delivery performance.

## What this project asks

The project is built around three practical questions:

1. **Where do comparable medicines show unusually wide historical price dispersion?**
2. **Which product-market combinations depend heavily on a small number of manufacturing suppliers?**
3. **Where do high procurement value, price dispersion, and supplier concentration combine into a useful review signal?**

The result is not an "inefficiency detector." Procurement prices can vary for legitimate reasons including contract terms, order size, freight, quality requirements, geography, and timing. The output is a **transparent review-priority system** that tells an analyst where deeper investigation may be worth the effort.

## Dataset

The first build uses the historical **SCMS Delivery History Dataset**, a public USAID/PEPFAR health-commodity procurement and shipment dataset.

After cleaning and restricting the analysis to comparable ARV pharmaceutical records, the analytical dataset contains:

- **8,542 transactions**
- **33 markets**
- **48 manufacturing suppliers**
- **92 product formulations**
- **$1.41B in historical procurement value**
- deliveries spanning **2006-08-11 to 2015-09-14**

The repository does not store the raw source file. The pipeline downloads it during execution and writes the cleaned analytical dataset to `data/processed/`.

## Headline findings

### 1. South Africa repeatedly appears in the highest review-priority combinations

The top-ranked signal is **Zidovudine 300mg, 60-tablet packs in South Africa**:

- 93 transactions
- 4 manufacturing suppliers
- median pack price: **$16.09**
- normalized IQR price dispersion: **1.07**
- top manufacturing site represented about **97% of observed procurement value**
- review-priority score: **84.6 / 100**

This does **not** imply overpricing. It indicates a combination of meaningful historical spend, broad price spread, and concentrated manufacturing exposure that deserves closer contextual review.

### 2. Efavirenz 600mg shows large within-market price variation

For **Efavirenz 600mg, 30-tablet packs in South Africa**:

- 144 transactions
- 5 manufacturing suppliers
- median pack price: **$11.27**
- observed pack prices ranged from **$4.26 to $21.66**
- normalized IQR price dispersion: **1.01**
- top supplier share: about **78%**
- review score: **81.9**

### 3. Supplier concentration and price dispersion do not always move together

For **Tenofovir disoproxil fumarate 300mg in South Africa**, the model finds:

- 129 transactions
- 6 manufacturing suppliers
- median pack price: **$7.82**
- high normalized price dispersion: **1.78**
- lower supplier concentration than several other top signals
- top supplier share: about **51%**

That is useful because it separates two very different procurement questions: "Are prices dispersed?" and "Is supply concentrated?"

### 4. Historical procurement value is highly concentrated among a few manufacturing suppliers

The largest manufacturing suppliers by observed procurement value include:

| Manufacturing supplier | Transactions | Markets | Procurement value |
|---|---:|---:|---:|
| Mylan (formerly Matrix) Nashik | 1,413 | 26 | $435.7M |
| Aurobindo Unit III, India | 3,169 | 29 | $335.5M |
| Hetero Unit III Hyderabad | 869 | 26 | $213.9M |
| Cipla, Goa, India | 664 | 21 | $130.6M |
| Strides, Bangalore, India | 540 | 22 | $84.6M |

These figures describe the historical dataset only, not current market share.

## Review-priority framework

Each sufficiently observed product-market combination is scored using three components:

```
Review Priority =
    35% procurement-value rank
  + 35% price-dispersion rank
  + 30% supplier-concentration rank
```

Where:

- **Procurement value** captures commercial significance.
- **Price dispersion** uses the interquartile range divided by median pack price.
- **Supplier concentration** uses a value-weighted Herfindahl-Hirschman Index (HHI) across manufacturing sites.

Only product-market combinations with at least **5 transactions** are scored. The current build scores **375 combinations**.

## Outputs

The pipeline creates:

- `data/processed/arv_procurement_clean.csv` — cleaned analytical dataset
- `outputs/product_market_signals.csv` — ranked product-market review signals
- `outputs/supplier_summary.csv` — manufacturing supplier footprint
- `outputs/country_summary.csv` — market-level procurement and delivery summary
- `outputs/executive_summary.json` — machine-readable headline metrics
- `outputs/dashboard.html` — lightweight executive dashboard
- `outputs/figures/` — decision-oriented charts
- `presentation/5-slide-story.md` — concise executive presentation narrative

## Dashboard

Open `outputs/dashboard.html` locally to explore the headline metrics and ranking table.

The dashboard intentionally stays lightweight: the point is to demonstrate the analytical logic and decision workflow, not to bury the user under filters because dashboards apparently become "enterprise" once they have seventeen dropdowns.

## Automation concept

A production version of this workflow could:

1. ingest public tender and procurement feeds,
2. standardize product and formulation identifiers,
3. benchmark new observations against historical price distributions,
4. monitor manufacturing-supplier concentration,
5. flag unusual price or supply signals,
6. route high-priority observations into a commercial or procurement review queue.

That turns a one-off analysis into a repeatable intelligence system.

## Reproducibility

The GitHub Actions workflow:

1. downloads the public source dataset,
2. cleans and standardizes the records,
3. calculates procurement metrics,
4. builds review-priority scores,
5. regenerates output tables, charts, and dashboard,
6. commits refreshed outputs back to the repository.

The build can also be run locally:

```bash
pip install -r requirements.txt
python src/analyze.py
```

## Important analytical caveats

- The dataset is **historical**, not current market pricing.
- Observed price differences can reflect legitimate procurement conditions.
- Manufacturing site is used as the supplier entity because the source `Vendor` field sometimes contains distribution/intermediary labels such as **SCMS from RDC**.
- Supplier concentration therefore represents concentration across recorded manufacturing sites, not necessarily corporate-parent market share.
- Delivery dates may reflect operational revisions not visible in the source.
- This is a prioritization model for further review, not a causal model or procurement-performance verdict.

## Data source

Historical SCMS Delivery History Dataset:
https://github.com/MSadriAghdam/Supply-Chain-Prediction_Neural-Network-ML/blob/main/SCMS_Delivery_History_Dataset.csv

For future extension, the Global Fund's Price & Quality Reporting database provides public transaction-level procurement information:
https://www.theglobalfund.org/en/sourcing-management/price-quality-reporting/

## Stack

Python · pandas · NumPy · Matplotlib · GitHub Actions
