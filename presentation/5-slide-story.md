# 5-Slide Executive Story

## Slide 1 — The problem: procurement data exist, but decision signals are buried

Global-health procurement systems generate transaction-level data on products, suppliers, prices, quantities, delivery, and geography.

The analytical challenge is not simply "find the cheapest price." A useful intelligence layer needs to distinguish between:

- meaningful price dispersion,
- legitimate procurement variation,
- supplier concentration,
- commercial scale,
- and signals worth investigating further.

**Prototype question:** Which product-market combinations should a procurement or commercial analyst review first?

---

## Slide 2 — Data and analytical approach

### Historical public procurement data

- 8,542 cleaned ARV procurement transactions
- 33 markets
- 48 manufacturing suppliers
- 92 comparable formulations
- $1.41B procurement value
- 2006–2015 delivery history

### Method

For each product-market combination with at least 5 observations:

1. standardize medicine + dosage + form + pack size,
2. calculate median price and interquartile price spread,
3. measure manufacturing-supplier concentration using HHI,
4. rank combinations by procurement value,
5. combine the three into a transparent review-priority score.

---

## Slide 3 — Signal 1: price dispersion can remain large even within a fixed formulation

### Efavirenz 600mg, 30 tablets — South Africa

- 144 transactions
- 5 manufacturing suppliers
- median pack price: $11.27
- observed range: $4.26–$21.66
- normalized IQR price dispersion: 1.01
- top supplier share: ~78%
- review score: 81.9 / 100

**Interpretation**

The spread is large enough to justify asking what explains the difference: timing, contract structure, purchase size, manufacturer, distribution route, or other procurement conditions.

The point is not "this price is wrong." The point is "this pattern deserves explanation."

---

## Slide 4 — Signal 2: price dispersion and supplier concentration are different risks

### Tenofovir DF 300mg, 30 tablets — South Africa

- 129 transactions
- 6 manufacturing suppliers
- median pack price: $7.82
- normalized price dispersion: 1.78
- top supplier share: ~51%

This combination has very high historical price dispersion but materially lower supplier concentration than several other top-ranked signals.

### Why that matters

A decision system should distinguish:

- **price risk / negotiation signal**
- **supplier concentration / resilience signal**
- **commercial significance**

Collapsing them into one raw metric hides the reason a market deserves attention.

---

## Slide 5 — From analysis to an automated procurement-intelligence workflow

### Prototype today

Public procurement data  
→ product normalization  
→ price benchmarking  
→ supplier concentration  
→ ranked review signals  
→ executive dashboard

### Production concept

Tender and procurement feeds  
→ automated extraction / agents  
→ medicine + supplier entity resolution  
→ historical benchmarking  
→ anomaly and concentration monitoring  
→ commercial/procurement review queue

### Principle

Use AI and automation to reduce the cost of finding signals.

Keep the decision logic transparent enough that a human analyst can explain **why** something was flagged.
