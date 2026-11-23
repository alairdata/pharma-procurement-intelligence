from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .common import RAW, STATE_DIR, STAGING, download, parse_numeric, product_key, sha256_file


def _state_path() -> Path:
    return STATE_DIR / "source_hashes.json"


def load_state() -> dict:
    p = _state_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_state(state: dict) -> None:
    _state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")


def ingest_scms(url: str) -> tuple[pd.DataFrame, str]:
    raw = RAW / "scms_delivery_history.csv"
    download(url, raw)
    source_hash = sha256_file(raw)

    df = pd.read_csv(raw, low_memory=False)
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
    df = df[[c for c in rename.values() if c in df.columns]].copy()
    df = df[df["product_group"].astype("string").str.upper().eq("ARV")].copy()

    for c in ["quantity", "line_item_value_usd", "pack_price_usd", "unit_price_usd",
              "freight_cost_usd", "weight_kg", "units_per_pack"]:
        if c in df:
            df[c] = parse_numeric(df[c])

    for c in ["scheduled_delivery_date", "delivered_date"]:
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    text_cols = [
        "country", "vendor", "molecule", "dosage", "dosage_form",
        "item_description", "manufacturing_site", "shipment_mode",
        "fulfill_via", "sub_classification", "brand",
    ]
    for c in text_cols:
        if c in df:
            df[c] = (
                df[c].astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
                .replace({"<NA>": pd.NA, "nan": pd.NA, "": pd.NA})
            )

    df["supplier_entity"] = df["manufacturing_site"].where(
        df["manufacturing_site"].notna(), df["vendor"]
    )
    df["product_key"] = [
        product_key(m, d, f, p)
        for m, d, f, p in zip(df["molecule"], df["dosage"], df["dosage_form"], df["units_per_pack"])
    ]
    df["source"] = "SCMS"
    df["source_record_id"] = "scms-" + df.index.astype(str)

    if {"scheduled_delivery_date", "delivered_date"}.issubset(df.columns):
        df["delivery_delay_days"] = (df["delivered_date"] - df["scheduled_delivery_date"]).dt.days
        df["late_delivery"] = df["delivery_delay_days"].gt(0)

    df = df[
        df["country"].notna()
        & df["supplier_entity"].notna()
        & df["pack_price_usd"].gt(0)
        & df["quantity"].gt(0)
        & df["line_item_value_usd"].gt(0)
    ].copy()

    return df, source_hash


def _gf_name(product: str, description: str) -> tuple[str, str, str]:
    # Preserve a readable label while extracting broad formulation components.
    p = str(product or "").strip()
    d = str(description or "").strip()
    strength, _, form = d.partition("|")
    return p, strength.strip(), form.strip()


def ingest_global_fund_pqr(url: str) -> tuple[pd.DataFrame, str]:
    raw = RAW / "global_fund_pqr_kenya.csv"
    download(url, raw)
    source_hash = sha256_file(raw)

    df = pd.read_csv(raw, dtype=str, low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    required = {"Measure Names", "Measure Values", "Country/Teritorry", "Product", "Description"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Global Fund PQR schema changed; missing columns: {sorted(missing)}")

    df["Measure Values"] = parse_numeric(df["Measure Values"])
    idx = [c for c in df.columns if c not in ("Measure Names", "Measure Values")]
    wide = (
        df.fillna({c: "" for c in idx})
        .pivot_table(index=idx, columns="Measure Names", values="Measure Values", aggfunc="first")
        .reset_index()
    )

    def col(name: str, default=None):
        return wide[name] if name in wide.columns else pd.Series(default, index=wide.index)

    parsed = [_gf_name(p, d) for p, d in zip(wide["Product"], wide["Description"])]
    out = pd.DataFrame({
        "country": wide["Country/Teritorry"].str.strip(),
        "molecule": [x[0] for x in parsed],
        "dosage": [x[1] for x in parsed],
        "dosage_form": [x[2] for x in parsed],
        "units_per_pack": pd.to_numeric(col("Nb of Suom in Pack"), errors="coerce"),
        "quantity": pd.to_numeric(col("Pack quantity"), errors="coerce"),
        "line_item_value_usd": pd.to_numeric(col("Total Product Cost (USD)"), errors="coerce"),
        "pack_price_usd": pd.to_numeric(col("Unit Cost (USD)"), errors="coerce"),
        "vendor": wide.get("Supplier/Agent/Manufacturer/Intermediatry", pd.Series(index=wide.index, dtype="string")).str.strip(),
        "manufacturing_site": wide.get("Manufacturer", pd.Series(index=wide.index, dtype="string")).str.strip(),
        "delivered_date": pd.to_datetime(col("Actual Delivery Date"), errors="coerce"),
        "scheduled_delivery_date": pd.NaT,
        "source": "Global Fund PQR",
        "source_record_id": ["pqr-" + str(i) for i in range(len(wide))],
    })

    out["supplier_entity"] = out["manufacturing_site"].where(
        out["manufacturing_site"].notna() & out["manufacturing_site"].ne(""), out["vendor"]
    )
    out["product_key"] = [
        product_key(m, d, f, p)
        for m, d, f, p in zip(out["molecule"], out["dosage"], out["dosage_form"], out["units_per_pack"])
    ]
    out["delivery_delay_days"] = pd.NA
    out["late_delivery"] = pd.NA

    out = out[
        out["country"].notna()
        & out["supplier_entity"].notna()
        & out["pack_price_usd"].gt(0)
        & out["quantity"].gt(0)
        & out["line_item_value_usd"].gt(0)
    ].copy()

    return out, source_hash


def run_ingestion(config: dict) -> dict:
    old_state = load_state()
    new_state = dict(old_state)
    results = {}

    adapters = {
        "scms": ingest_scms,
        "global_fund_pqr_kenya": ingest_global_fund_pqr,
    }

    for name, source in config["sources"].items():
        if not source.get("enabled", True):
            continue
        try:
            df, source_hash = adapters[name](source["url"])
            changed = old_state.get(name) != source_hash
            staged = STAGING / f"{name}.csv"
            if changed or not staged.exists():
                df.to_csv(staged, index=False)
            new_state[name] = source_hash
            results[name] = {
                "status": "ok",
                "changed": changed,
                "rows": int(len(df)),
                "hash": source_hash,
            }
        except Exception as exc:
            if source.get("required", False):
                raise
            results[name] = {
                "status": "degraded",
                "changed": False,
                "rows": 0,
                "error": str(exc),
            }

    save_state(new_state)
    (STATE_DIR / "source_health.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results
