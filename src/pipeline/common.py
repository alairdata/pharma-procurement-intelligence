from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
STAGING = ROOT / "data" / "staging"
MARTS = ROOT / "data" / "marts"
STATE_DIR = ROOT / "data" / "state"
OUT = ROOT / "outputs"
FIG = OUT / "figures"
CONFIG_PATH = ROOT / "config" / "pipeline.json"


def ensure_dirs() -> None:
    for p in (RAW, STAGING, MARTS, STATE_DIR, OUT, FIG):
        p.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "pharma-procurement-intelligence/2.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        path.write_bytes(r.read())


def parse_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype("string")
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def norm_text(value: object) -> str:
    if pd.isna(value):
        return "unknown"
    s = str(value).lower()
    s = re.sub(r"[^a-z0-9./+ -]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def product_key(molecule: object, dosage: object, form: object, pack: object) -> str:
    pack_s = "unknown" if pd.isna(pack) else str(pack)
    return " | ".join([norm_text(molecule), norm_text(dosage), norm_text(form), pack_s])
