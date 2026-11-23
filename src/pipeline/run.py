from __future__ import annotations

import json

from .alerts import build_alerts
from .common import ensure_dirs, load_config
from .ingest import run_ingestion
from .quality import validate
from .signals import build_signals
from .transform import build_canonical_table


def main() -> None:
    ensure_dirs()
    config = load_config()

    health = run_ingestion(config)
    fact = build_canonical_table(health)
    quality = validate(fact)
    result = build_signals(fact, config)
    build_alerts(fact, result["signals"], config)

    print(json.dumps({
        "sources": health,
        "quality": quality,
        "summary": result["summary"],
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
