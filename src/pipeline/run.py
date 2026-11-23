from __future__ import annotations

import json

from .alerts import build_alerts
from .common import ensure_dirs, load_config
from .ingest import run_ingestion
from .quality import validate
from .publish import publish
from .signals import build_signals
from .transform import build_canonical_table
from .warehouse import build_warehouse


def main() -> None:
    ensure_dirs()
    config = load_config()

    health = run_ingestion(config)
    fact = build_canonical_table(health)
    quality = validate(fact)
    result = build_signals(fact, config)
    build_alerts(fact, result["signals"], config)
    warehouse = build_warehouse(
        fact,
        result["signals"],
        result["supplier_summary"],
        result["country_summary"],
    )
    publish(
        fact,
        result["signals"],
        result["supplier_summary"],
        result["country_summary"],
        result["summary"],
        health,
    )

    print(json.dumps({
        "sources": health,
        "quality": quality,
        "summary": result["summary"],
        "warehouse": warehouse,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
