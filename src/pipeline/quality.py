from __future__ import annotations

import json

import pandas as pd

from .common import OUT


class DataQualityError(RuntimeError):
    pass


def validate(df: pd.DataFrame) -> dict:
    checks = {}

    checks["rows_positive"] = len(df) > 0
    checks["no_negative_prices"] = bool((df["pack_price_usd"].dropna() > 0).all())
    checks["no_negative_quantities"] = bool((df["quantity"].dropna() > 0).all())
    checks["country_completeness"] = float(df["country"].notna().mean())
    checks["supplier_completeness"] = float(df["supplier_entity"].notna().mean())
    checks["product_key_completeness"] = float(df["product_key"].notna().mean())
    checks["duplicate_source_ids"] = int(df.duplicated(["source", "source_record_id"]).sum())

    hard_failures = [
        not checks["rows_positive"],
        not checks["no_negative_prices"],
        not checks["no_negative_quantities"],
        checks["country_completeness"] < 0.98,
        checks["supplier_completeness"] < 0.95,
        checks["product_key_completeness"] < 0.98,
        checks["duplicate_source_ids"] > 0,
    ]

    checks["passed"] = not any(hard_failures)
    (OUT / "data_quality_report.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")

    if not checks["passed"]:
        raise DataQualityError(f"Data quality gate failed: {checks}")

    return checks
