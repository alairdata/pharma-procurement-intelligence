from __future__ import annotations

import json
import re

import pandas as pd

from .common import MARTS, ROOT, STAGING


def canonical_supplier(value: object) -> str:
    if pd.isna(value):
        return "unknown"
    s = re.sub(r"\s+", " ", str(value)).strip()
    replacements = {
        "Mylan (formerly Matrix) Nashik": "Mylan / Matrix Nashik",
        "Strides, Bangalore, India.": "Strides Bangalore",
        "Aurobindo Unit III, India": "Aurobindo Unit III",
        "Aurobindo Unit VII, IN": "Aurobindo Unit VII",
        "Hetero Unit III Hyderabad IN": "Hetero Unit III Hyderabad",
        "Cipla, Goa, India": "Cipla Goa",
    }
    return replacements.get(s, s)


def build_canonical_table(source_health: dict) -> pd.DataFrame:
    frames = []
    for name, health in source_health.items():
        path = STAGING / f"{name}.csv"
        if health["status"] == "ok" and path.exists():
            frames.append(pd.read_csv(path, low_memory=False))

    if not frames:
        raise RuntimeError("No healthy staged sources available")

    df = pd.concat(frames, ignore_index=True, sort=False)

    for c in ["delivered_date", "scheduled_delivery_date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    numeric = [
        "quantity", "line_item_value_usd", "pack_price_usd", "unit_price_usd",
        "freight_cost_usd", "weight_kg", "units_per_pack", "delivery_delay_days",
    ]
    for c in numeric:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["supplier_entity_raw"] = df["supplier_entity"]
    df["supplier_entity"] = df["supplier_entity"].map(canonical_supplier)

    # One canonical record identity across sources.
    df["record_key"] = df["source"].astype(str) + "::" + df["source_record_id"].astype(str)
    df = df.drop_duplicates("record_key", keep="last")

    df.to_csv(MARTS / "fact_procurement.csv", index=False)

    dim_product = (
        df[["product_key", "molecule", "dosage", "dosage_form", "units_per_pack"]]
        .drop_duplicates()
        .sort_values("product_key")
    )
    dim_product.to_csv(MARTS / "dim_product.csv", index=False)

    dim_supplier = (
        df[["supplier_entity", "supplier_entity_raw"]]
        .drop_duplicates()
        .sort_values(["supplier_entity", "supplier_entity_raw"])
    )
    dim_supplier.to_csv(MARTS / "dim_supplier.csv", index=False)

    dim_market = df[["country"]].drop_duplicates().sort_values("country")
    dim_market.to_csv(MARTS / "dim_market.csv", index=False)

    return df
