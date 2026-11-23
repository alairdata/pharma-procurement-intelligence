from __future__ import annotations

import json
import sqlite3

import pandas as pd

from .common import ROOT

WAREHOUSE_DIR = ROOT / "data" / "warehouse"
WAREHOUSE_PATH = WAREHOUSE_DIR / "procurement.db"


def build_warehouse(
    fact: pd.DataFrame,
    signals: pd.DataFrame,
    supplier_summary: pd.DataFrame,
    country_summary: pd.DataFrame,
) -> dict:
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(WAREHOUSE_PATH) as con:
        fact.to_sql("fact_procurement", con, if_exists="replace", index=False)
        signals.to_sql("mart_product_market_signals", con, if_exists="replace", index=False)
        supplier_summary.to_sql("mart_supplier_summary", con, if_exists="replace", index=False)
        country_summary.to_sql("mart_country_summary", con, if_exists="replace", index=False)

        con.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_fact_market_product
              ON fact_procurement(country, product_key);
            CREATE INDEX IF NOT EXISTS idx_fact_supplier
              ON fact_procurement(supplier_entity);

            DROP VIEW IF EXISTS vw_high_priority_signals;
            CREATE VIEW vw_high_priority_signals AS
            SELECT *
            FROM mart_product_market_signals
            WHERE review_priority_score >= 70
            ORDER BY review_priority_score DESC;

            DROP VIEW IF EXISTS vw_large_markets;
            CREATE VIEW vw_large_markets AS
            SELECT *
            FROM mart_country_summary
            WHERE total_value_usd >= 10000000
            ORDER BY total_value_usd DESC;
            """
        )

        counts = {
            "fact_procurement": int(pd.read_sql_query("SELECT COUNT(*) n FROM fact_procurement", con)["n"].iloc[0]),
            "mart_product_market_signals": int(pd.read_sql_query("SELECT COUNT(*) n FROM mart_product_market_signals", con)["n"].iloc[0]),
            "mart_supplier_summary": int(pd.read_sql_query("SELECT COUNT(*) n FROM mart_supplier_summary", con)["n"].iloc[0]),
            "mart_country_summary": int(pd.read_sql_query("SELECT COUNT(*) n FROM mart_country_summary", con)["n"].iloc[0]),
        }

    (WAREHOUSE_DIR / "warehouse_manifest.json").write_text(
        json.dumps({"engine": "SQLite", "tables": counts}, indent=2),
        encoding="utf-8",
    )
    return counts
