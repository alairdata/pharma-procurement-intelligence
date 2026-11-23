from __future__ import annotations

import json
import math
import re
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
OUT = ROOT / "outputs"
FIG = OUT / "figures"

SOURCE_URL = (
    "https://raw.githubusercontent.com/MSadriAghdam/"
    "Supply-Chain-Prediction_Neural-Network-ML/refs/heads/main/"
    "SCMS_Delivery_History_Dataset.csv"
)
RAW_FILE = RAW / "scms_delivery_history.csv"


def ensure_dirs() -> None:
    for p in (RAW, PROCESSED, OUT, FIG):
        p.mkdir(parents=True, exist_ok=True)


def download_source() -> None:
    if RAW_FILE.exists() and RAW_FILE.stat().st_size > 1_000_000:
        return
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "procurement-intelligence/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        RAW_FILE.write_bytes(r.read())


def parse_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype("string")
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def clean() -> pd.DataFrame:
    df = pd.read_csv(RAW_FILE, low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    rename = {
        "Country": "country",
        "Product Group": "product_group",
        "Sub Classification": "sub_classification",
        "Vendor": "vendor",
        "Item Description": "item_description",
        "Molecule/Test Type": "molecule",
        "Brand": "brand",
        "Dosage": "dosage",
        "Dosage Form": "dosage_form",
        "Unit of Measure (Per Pack)": "units_per_pack",
        "Line Item Quantity": "quantity",
        "Line Item Value": "line_item_value_usd",
        "Pack Price": "pack_price_usd",
        "Unit Price": "unit_price_usd",
        "Manufacturing Site": "manufacturing_site",
        "Shipment Mode": "shipment_mode",
        "Fulfill Via": "fulfill_via",
        "Scheduled Delivery Date": "scheduled_delivery_date",
        "Delivered to Client Date": "delivered_date",
        "Freight Cost (USD)": "freight_cost_usd",
        "Weight (Kilograms)": "weight_kg",
    }
    df = df.rename(columns=rename)

    keep = [c for c in rename.values() if c in df.columns]
    df = df[keep].copy()

    for c in ["quantity", "line_item_value_usd", "pack_price_usd", "unit_price_usd",
              "freight_cost_usd", "weight_kg", "units_per_pack"]:
        if c in df.columns:
            df[c] = parse_numeric(df[c])

    for c in ["scheduled_delivery_date", "delivered_date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Comparable pharmaceutical focus. The source also contains HIV diagnostics.
    if "product_group" in df.columns:
        df = df[df["product_group"].astype("string").str.upper().eq("ARV")].copy()

    text_cols = [
        "country", "vendor", "molecule", "dosage", "dosage_form",
        "item_description", "manufacturing_site", "shipment_mode", "fulfill_via",
        "sub_classification", "brand"
    ]
    for c in text_cols:
        if c in df.columns:
            df[c] = (
                df[c].astype("string")
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
                .replace({"<NA>": pd.NA, "nan": pd.NA, "": pd.NA})
            )

    # Product key holds formulation constant enough for transparent comparisons.
    def norm(v: object) -> str:
        if pd.isna(v):
            return "unknown"
        s = str(v).lower()
        s = re.sub(r"[^a-z0-9./+ -]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    df["product_key"] = (
        df.get("molecule", pd.Series(index=df.index, dtype="string")).map(norm)
        + " | "
        + df.get("dosage", pd.Series(index=df.index, dtype="string")).map(norm)
        + " | "
        + df.get("dosage_form", pd.Series(index=df.index, dtype="string")).map(norm)
        + " | "
        + df.get("units_per_pack", pd.Series(index=df.index, dtype="float")).fillna(-1).astype(str)
    )

    if {"scheduled_delivery_date", "delivered_date"}.issubset(df.columns):
        df["delivery_delay_days"] = (
            df["delivered_date"] - df["scheduled_delivery_date"]
        ).dt.days
        df["late_delivery"] = df["delivery_delay_days"].gt(0)

    # Use manufacturing site as the supplier entity where available. The raw
    # Vendor field sometimes contains "SCMS from RDC", which is a distribution
    # route/intermediary label rather than a true manufacturer.
    df["supplier_entity"] = df["manufacturing_site"].where(
        df["manufacturing_site"].notna(), df["vendor"]
    )

    df = df[
        df["country"].notna()
        & df["vendor"].notna()
        & df["pack_price_usd"].gt(0)
        & df["quantity"].gt(0)
        & df["line_item_value_usd"].gt(0)
    ].copy()

    df.to_csv(PROCESSED / "arv_procurement_clean.csv", index=False)
    return df


def hhi(values: pd.Series) -> float:
    x = values.dropna()
    if x.empty or x.sum() <= 0:
        return np.nan
    shares = x / x.sum()
    return float((shares ** 2).sum())


def percentile_rank(s: pd.Series) -> pd.Series:
    return s.rank(method="average", pct=True).fillna(0)


def analyse(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    gcols = ["country", "product_key"]

    base = df.groupby(gcols).agg(
        transactions=("product_key", "size"),
        total_quantity=("quantity", "sum"),
        total_value_usd=("line_item_value_usd", "sum"),
        median_pack_price_usd=("pack_price_usd", "median"),
        p25_pack_price_usd=("pack_price_usd", lambda x: x.quantile(.25)),
        p75_pack_price_usd=("pack_price_usd", lambda x: x.quantile(.75)),
        min_pack_price_usd=("pack_price_usd", "min"),
        max_pack_price_usd=("pack_price_usd", "max"),
        supplier_count=("supplier_entity", "nunique"),
    ).reset_index()

    base["iqr_pack_price_usd"] = base["p75_pack_price_usd"] - base["p25_pack_price_usd"]
    base["normalized_price_dispersion"] = (
        base["iqr_pack_price_usd"] / base["median_pack_price_usd"]
    ).replace([np.inf, -np.inf], np.nan)

    supplier_value = (
        df.groupby(gcols + ["supplier_entity"], as_index=False)["line_item_value_usd"].sum()
    )

    conc = (
        supplier_value.groupby(gcols)
        .apply(
            lambda x: pd.Series({
                "supplier_hhi": hhi(x["line_item_value_usd"]),
                "top_supplier_share": (
                    x["line_item_value_usd"].max() / x["line_item_value_usd"].sum()
                    if x["line_item_value_usd"].sum() > 0 else np.nan
                ),
                "top_supplier": x.loc[x["line_item_value_usd"].idxmax(), "supplier_entity"],
            }),
            include_groups=False,
        )
        .reset_index()
    )

    signals = base.merge(conc, on=gcols, how="left")
    signals = signals[signals["transactions"] >= 5].copy()

    # Transparent review-priority score, not a claim of inefficiency.
    signals["value_rank"] = percentile_rank(np.log1p(signals["total_value_usd"]))
    signals["dispersion_rank"] = percentile_rank(signals["normalized_price_dispersion"].fillna(0))
    signals["concentration_rank"] = percentile_rank(signals["supplier_hhi"].fillna(0))
    signals["review_priority_score"] = (
        100 * (
            0.35 * signals["value_rank"]
            + 0.35 * signals["dispersion_rank"]
            + 0.30 * signals["concentration_rank"]
        )
    ).round(1)

    signals = signals.sort_values(
        ["review_priority_score", "total_value_usd"], ascending=False
    )
    signals.to_csv(OUT / "product_market_signals.csv", index=False)

    supplier_summary = (
        df.groupby("supplier_entity", as_index=False)
        .agg(
            transactions=("supplier_entity", "size"),
            countries=("country", "nunique"),
            products=("product_key", "nunique"),
            total_value_usd=("line_item_value_usd", "sum"),
            total_quantity=("quantity", "sum"),
            median_pack_price_usd=("pack_price_usd", "median"),
        )
        .sort_values("total_value_usd", ascending=False)
    )
    supplier_summary.to_csv(OUT / "supplier_summary.csv", index=False)

    country_summary = (
        df.groupby("country", as_index=False)
        .agg(
            transactions=("country", "size"),
            suppliers=("supplier_entity", "nunique"),
            products=("product_key", "nunique"),
            total_value_usd=("line_item_value_usd", "sum"),
            total_quantity=("quantity", "sum"),
            median_pack_price_usd=("pack_price_usd", "median"),
            late_delivery_rate=("late_delivery", "mean"),
        )
        .sort_values("total_value_usd", ascending=False)
    )
    country_summary["late_delivery_rate"] = (100 * country_summary["late_delivery_rate"]).round(1)
    country_summary.to_csv(OUT / "country_summary.csv", index=False)

    date_min = df["delivered_date"].min()
    date_max = df["delivered_date"].max()
    summary = {
        "records_analyzed": int(len(df)),
        "countries": int(df["country"].nunique()),
        "suppliers": int(df["supplier_entity"].nunique()),
        "product_formulations": int(df["product_key"].nunique()),
        "total_procurement_value_usd": round(float(df["line_item_value_usd"].sum()), 2),
        "date_start": None if pd.isna(date_min) else str(date_min.date()),
        "date_end": None if pd.isna(date_max) else str(date_max.date()),
        "signal_groups_scored": int(len(signals)),
        "top_review_signals": signals.head(10)[
            [
                "country", "product_key", "transactions", "supplier_count",
                "median_pack_price_usd", "normalized_price_dispersion",
                "supplier_hhi", "top_supplier_share", "top_supplier",
                "total_value_usd", "review_priority_score"
            ]
        ].replace({np.nan: None}).to_dict(orient="records"),
    }

    with open(OUT / "executive_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return signals, supplier_summary, country_summary, summary


def charts(signals: pd.DataFrame, supplier_summary: pd.DataFrame, country_summary: pd.DataFrame) -> None:
    if not country_summary.empty:
        top = country_summary.head(12).sort_values("total_value_usd")
        plt.figure(figsize=(9, 6))
        plt.barh(top["country"], top["total_value_usd"] / 1_000_000)
        plt.xlabel("Procurement value (USD millions)")
        plt.title("Top markets by historical ARV procurement value")
        plt.tight_layout()
        plt.savefig(FIG / "market_value.png", dpi=160)
        plt.close()

    if not supplier_summary.empty:
        top = supplier_summary.head(12).sort_values("total_value_usd")
        plt.figure(figsize=(9, 6))
        plt.barh(top["supplier_entity"], top["total_value_usd"] / 1_000_000)
        plt.xlabel("Procurement value (USD millions)")
        plt.title("Top manufacturing suppliers by historical procurement value")
        plt.tight_layout()
        plt.savefig(FIG / "supplier_value.png", dpi=160)
        plt.close()

    if not signals.empty:
        s = signals.head(20).sort_values("review_priority_score")
        labels = [f"{c} | {p.split(' | ')[0]}" for c, p in zip(s["country"], s["product_key"])]
        plt.figure(figsize=(10, 8))
        plt.barh(labels, s["review_priority_score"])
        plt.xlabel("Review-priority score (0–100)")
        plt.title("Highest-priority product-market combinations for deeper review")
        plt.tight_layout()
        plt.savefig(FIG / "review_priority.png", dpi=160)
        plt.close()


def html_dashboard(
    signals: pd.DataFrame,
    supplier_summary: pd.DataFrame,
    country_summary: pd.DataFrame,
    summary: dict,
) -> None:
    def money(x: float) -> str:
        if x >= 1_000_000:
            return f"${x/1_000_000:,.1f}M"
        if x >= 1_000:
            return f"${x/1_000:,.1f}K"
        return f"${x:,.0f}"

    cards = [
        ("Transactions", f"{summary['records_analyzed']:,}"),
        ("Markets", f"{summary['countries']:,}"),
        ("Suppliers", f"{summary['suppliers']:,}"),
        ("Procurement value", money(summary["total_procurement_value_usd"])),
    ]

    top_signals = signals.head(12).copy()
    top_signals["product"] = top_signals["product_key"].str.split(" \| ").str[0]
    top_signals["price_dispersion"] = (100 * top_signals["normalized_price_dispersion"]).round(1)
    top_signals["top_supplier_pct"] = (100 * top_signals["top_supplier_share"]).round(1)

    table = top_signals[
        [
            "country", "product", "transactions", "supplier_count",
            "price_dispersion", "top_supplier_pct", "review_priority_score"
        ]
    ].rename(columns={
        "country": "Market",
        "product": "Medicine",
        "transactions": "Transactions",
        "supplier_count": "Suppliers",
        "price_dispersion": "Price dispersion (%)",
        "top_supplier_pct": "Top supplier share (%)",
        "review_priority_score": "Review score",
    }).to_html(index=False, classes="data-table", border=0)

    card_html = "".join(
        f'<div class="card"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in cards
    )

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pharmaceutical Procurement Intelligence</title>
<style>
body{{font-family:Inter,Arial,sans-serif;margin:0;background:#f6f7f9;color:#15171a}}
main{{max-width:1100px;margin:auto;padding:48px 24px}}
h1{{font-size:38px;margin-bottom:8px}} .sub{{color:#5c6570;margin-bottom:32px;max-width:800px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:28px 0}}
.card{{background:white;padding:20px;border-radius:14px;border:1px solid #e4e7eb}}
.card span{{display:block;color:#68717d;font-size:13px;margin-bottom:8px}} .card strong{{font-size:26px}}
section{{background:white;padding:24px;border-radius:14px;border:1px solid #e4e7eb;margin:18px 0}}
img{{width:100%;max-width:920px}}
.data-table{{border-collapse:collapse;width:100%;font-size:13px}}
.data-table th,.data-table td{{padding:10px;border-bottom:1px solid #eceff2;text-align:left}}
.note{{font-size:13px;color:#68717d;line-height:1.5}}
@media(max-width:800px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body><main>
<h1>Pharmaceutical Procurement Intelligence</h1>
<p class="sub">A compact decision-support prototype using historical public global-health procurement data to identify product-market combinations that deserve deeper pricing and supplier review.</p>
<div class="cards">{card_html}</div>
<section><h2>Highest review-priority signals</h2>{table}
<p class="note">The score combines historical procurement value, within-product price dispersion and supplier concentration. It is a screening signal, not a claim that a transaction is inefficient.</p></section>
<section><h2>Market footprint</h2><img src="figures/market_value.png" alt="Market procurement value"></section>
<section><h2>Supplier footprint</h2><img src="figures/supplier_value.png" alt="Supplier procurement value"></section>
<section><h2>Review-priority ranking</h2><img src="figures/review_priority.png" alt="Review priority"></section>
<section><h2>What this could become</h2>
<p>An automated intelligence workflow can ingest tender and procurement feeds, standardize medicine/formulation identifiers, benchmark new purchases against historical ranges, detect supplier-concentration shifts, and surface review alerts to commercial or procurement teams.</p>
</section>
<section><h2>Important context</h2>
<p class="note">This first build is historical and should not be read as a representation of current market prices. Procurement terms, freight, contract structure, quality requirements and geography can legitimately explain price variation. The project is designed to demonstrate a transparent analytical workflow rather than assert procurement wrongdoing.</p>
</section>
</main></body></html>"""
    (OUT / "dashboard.html").write_text(html, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    download_source()
    df = clean()
    signals, supplier_summary, country_summary, summary = analyse(df)
    charts(signals, supplier_summary, country_summary)
    html_dashboard(signals, supplier_summary, country_summary, summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
