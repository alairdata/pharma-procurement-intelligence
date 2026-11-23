from __future__ import annotations

import json

import pandas as pd

from .common import OUT


def build_alerts(df: pd.DataFrame, signal_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    cfg = config["signal_thresholds"]

    benchmark = (
        df.groupby(["country", "product_key"], as_index=False)
        .agg(historical_median_pack_price=("pack_price_usd", "median"))
    )
    records = df.merge(benchmark, on=["country", "product_key"], how="left")
    records["pct_above_market_product_median"] = (
        100 * (records["pack_price_usd"] / records["historical_median_pack_price"] - 1)
    )

    price_alerts = records[
        records["pct_above_market_product_median"] >= cfg["price_alert_pct_above_median"]
    ][[
        "source", "source_record_id", "country", "product_key", "supplier_entity",
        "pack_price_usd", "historical_median_pack_price", "pct_above_market_product_median"
    ]].copy()
    price_alerts["alert_type"] = "price_above_historical_market_median"

    concentration = signal_df[
        (signal_df["supplier_hhi"] >= cfg["supplier_hhi_alert"])
        | (signal_df["top_supplier_share"] >= cfg["top_supplier_share_alert"])
    ][[
        "country", "product_key", "supplier_count", "supplier_hhi",
        "top_supplier_share", "top_supplier", "review_priority_score"
    ]].copy()
    concentration["alert_type"] = "supplier_concentration"

    price_alerts.to_csv(OUT / "price_alerts.csv", index=False)
    concentration.to_csv(OUT / "supplier_concentration_alerts.csv", index=False)

    alert_summary = {
        "price_alert_records": int(len(price_alerts)),
        "concentration_alert_groups": int(len(concentration)),
        "thresholds": cfg,
    }
    (OUT / "alert_summary.json").write_text(json.dumps(alert_summary, indent=2), encoding="utf-8")
    return price_alerts
