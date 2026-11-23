from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .common import MARTS, OUT


def hhi(values: pd.Series) -> float:
    x = values.dropna()
    if x.empty or x.sum() <= 0:
        return np.nan
    shares = x / x.sum()
    return float((shares ** 2).sum())


def rank_pct(s: pd.Series) -> pd.Series:
    return s.rank(method="average", pct=True).fillna(0)


def build_signals(df: pd.DataFrame, config: dict) -> dict:
    min_tx = config["signal_thresholds"]["min_transactions"]
    gcols = ["country", "product_key"]

    base = df.groupby(gcols).agg(
        transactions=("record_key", "size"),
        sources=("source", "nunique"),
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

    s = base.merge(conc, on=gcols, how="left")
    s = s[s["transactions"] >= min_tx].copy()
    s["value_rank"] = rank_pct(np.log1p(s["total_value_usd"]))
    s["dispersion_rank"] = rank_pct(s["normalized_price_dispersion"].fillna(0))
    s["concentration_rank"] = rank_pct(s["supplier_hhi"].fillna(0))
    s["review_priority_score"] = (
        100 * (0.35*s["value_rank"] + 0.35*s["dispersion_rank"] + 0.30*s["concentration_rank"])
    ).round(1)
    s = s.sort_values(["review_priority_score", "total_value_usd"], ascending=False)
    s.to_csv(MARTS / "mart_product_market_signals.csv", index=False)
    s.to_csv(OUT / "product_market_signals.csv", index=False)

    supplier_summary = (
        df.groupby("supplier_entity", as_index=False)
        .agg(
            transactions=("record_key", "size"),
            sources=("source", "nunique"),
            countries=("country", "nunique"),
            products=("product_key", "nunique"),
            total_value_usd=("line_item_value_usd", "sum"),
            total_quantity=("quantity", "sum"),
            median_pack_price_usd=("pack_price_usd", "median"),
        )
        .sort_values("total_value_usd", ascending=False)
    )
    supplier_summary.to_csv(MARTS / "mart_supplier_summary.csv", index=False)
    supplier_summary.to_csv(OUT / "supplier_summary.csv", index=False)

    country_summary = (
        df.groupby("country", as_index=False)
        .agg(
            transactions=("record_key", "size"),
            sources=("source", "nunique"),
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
    country_summary.to_csv(MARTS / "mart_country_summary.csv", index=False)
    country_summary.to_csv(OUT / "country_summary.csv", index=False)

    summary = {
        "records_analyzed": int(len(df)),
        "sources_healthy": int(df["source"].nunique()),
        "countries": int(df["country"].nunique()),
        "suppliers": int(df["supplier_entity"].nunique()),
        "product_formulations": int(df["product_key"].nunique()),
        "total_procurement_value_usd": round(float(df["line_item_value_usd"].sum()), 2),
        "signal_groups_scored": int(len(s)),
        "top_review_signals": s.head(10).replace({np.nan: None}).to_dict(orient="records"),
    }
    (OUT / "executive_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"signals": s, "supplier_summary": supplier_summary, "country_summary": country_summary, "summary": summary}
