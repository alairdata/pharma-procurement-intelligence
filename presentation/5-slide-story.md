# 5-Slide Executive Story

## Slide 1 — From public procurement data to decision intelligence

Public procurement datasets contain useful commercial signals, but they are fragmented across sources and often require substantial cleaning before they can support decisions.

This prototype turns two public procurement sources into a repeatable intelligence workflow.

### Current build

- 9,291 canonical procurement records
- 2 healthy public data sources
- 33 markets
- 122 normalized supplier entities
- 235 product formulations
- ~$2.08B historical procurement value

**Question:** Which product-market combinations should a procurement or commercial analyst review first?

---

## Slide 2 — The system, not just the analysis

### Pipeline

Public sources  
→ source adapters  
→ raw ingestion  
→ SHA-256 change detection  
→ staging  
→ supplier/product normalization  
→ hard data-quality gates  
→ canonical fact + dimension tables  
→ analytical warehouse  
→ signal engine  
→ alerts  
→ dashboard + review brief

### Engineering controls

- required vs optional source behavior
- source-health reporting
- incremental staging refresh
- unit tests
- duplicate record checks
- serialized CI runs
- daily GitHub Actions orchestration

This makes the project reproducible and maintainable rather than a one-off notebook.

---

## Slide 3 — Review signals combine commercial scale, price dispersion and supply concentration

For each product-market combination with at least five observations:

**Review Priority =**
- 35% procurement-value percentile
- 35% normalized price-dispersion percentile
- 30% supplier-concentration percentile

### Example: Abacavir + Lamivudine, Kenya

- 22 transactions
- ~$19.1M historical procurement value
- median pack price: $3.59
- one recorded manufacturing supplier in this slice
- review score: 84.2

**Interpretation:** commercially material + concentrated supply + enough price movement to justify deeper review.

This is a screening signal, not a claim of inefficiency.

---

## Slide 4 — Alerts convert analysis into an operating workflow

The pipeline publishes a review queue using configurable thresholds.

### Current alerts

- 763 transaction-level price alerts
- 226 supplier-concentration alert groups

Default rules flag:

- prices 40%+ above the historical product-market median
- supplier HHI above 0.65
- top supplier share above 75%

Thresholds live in configuration rather than being buried in code.

That means the same system can support a different risk appetite without rewriting the analytical logic.

---

## Slide 5 — What this could become in production

### Today

Public procurement feeds  
→ normalization  
→ benchmarking  
→ concentration monitoring  
→ ranked review queue  
→ executive dashboard

### Next production layer

Tender portals + supplier feeds + internal purchase history  
→ automated extraction  
→ entity resolution  
→ historical benchmark comparison  
→ anomaly detection  
→ commercial / procurement review queue  
→ analyst feedback loop

### Principle

Use automation to reduce the cost of finding signals.

Keep the scoring logic transparent enough that a human can explain exactly why a transaction or market was flagged.
