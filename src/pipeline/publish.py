from __future__ import annotations

import html
import json

import matplotlib.pyplot as plt
import pandas as pd

from .common import FIG, OUT


def _money(v: float) -> str:
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:,.2f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:,.1f}M"
    if v >= 1_000:
        return f"${v/1_000:,.1f}K"
    return f"${v:,.0f}"


def publish(
    fact: pd.DataFrame,
    signals: pd.DataFrame,
    supplier_summary: pd.DataFrame,
    country_summary: pd.DataFrame,
    summary: dict,
    source_health: dict,
) -> None:
    FIG.mkdir(parents=True, exist_ok=True)

    top_markets = country_summary.head(12).sort_values("total_value_usd")
    plt.figure(figsize=(9, 6))
    plt.barh(top_markets["country"], top_markets["total_value_usd"] / 1_000_000)
    plt.xlabel("Procurement value (USD millions)")
    plt.title("Largest historical procurement markets")
    plt.tight_layout()
    plt.savefig(FIG / "market_value.png", dpi=160)
    plt.close()

    top_suppliers = supplier_summary.head(12).sort_values("total_value_usd")
    plt.figure(figsize=(9, 6))
    plt.barh(top_suppliers["supplier_entity"], top_suppliers["total_value_usd"] / 1_000_000)
    plt.xlabel("Procurement value (USD millions)")
    plt.title("Largest manufacturing suppliers")
    plt.tight_layout()
    plt.savefig(FIG / "supplier_value.png", dpi=160)
    plt.close()

    top_signals = signals.head(18).sort_values("review_priority_score")
    labels = [
        f"{c} | {str(p).split(' | ')[0]}"
        for c, p in zip(top_signals["country"], top_signals["product_key"])
    ]
    plt.figure(figsize=(10, 8))
    plt.barh(labels, top_signals["review_priority_score"])
    plt.xlabel("Review-priority score")
    plt.title("Highest-priority product-market signals")
    plt.tight_layout()
    plt.savefig(FIG / "review_priority.png", dpi=160)
    plt.close()

    display = signals.head(12).copy()
    display["Medicine"] = display["product_key"].astype(str).str.split(" \| ").str[0]
    display["Price dispersion"] = (100 * display["normalized_price_dispersion"]).round(1).astype(str) + "%"
    display["Top supplier share"] = (100 * display["top_supplier_share"]).round(1).astype(str) + "%"
    table = display[[
        "country", "Medicine", "transactions", "supplier_count",
        "Price dispersion", "Top supplier share", "review_priority_score"
    ]].rename(columns={
        "country": "Market",
        "transactions": "Transactions",
        "supplier_count": "Suppliers",
        "review_priority_score": "Review score",
    }).to_html(index=False, border=0, classes="data-table")

    health_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{html.escape(str(v.get('status')))}</td>"
        f"<td>{v.get('rows', 0):,}</td><td>{html.escape(str(v.get('changed')))}</td></tr>"
        for name, v in source_health.items()
    )

    cards = [
        ("Transactions", f"{summary['records_analyzed']:,}"),
        ("Healthy sources", f"{summary['sources_healthy']:,}"),
        ("Markets", f"{summary['countries']:,}"),
        ("Suppliers", f"{summary['suppliers']:,}"),
        ("Procurement value", _money(summary["total_procurement_value_usd"])),
        ("Signals scored", f"{summary['signal_groups_scored']:,}"),
    ]
    card_html = "".join(
        f'<div class="card"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in cards
    )

    page = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pharmaceutical Procurement Intelligence</title>
<style>
body{{font-family:Inter,Arial,sans-serif;margin:0;background:#f5f6f8;color:#17191d}}
main{{max-width:1120px;margin:auto;padding:48px 24px}}
h1{{font-size:40px;margin:0 0 8px}} .sub{{color:#606975;max-width:850px;line-height:1.5}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:28px 0}}
.card,section{{background:#fff;border:1px solid #e4e7eb;border-radius:14px}}
.card{{padding:20px}} .card span{{display:block;color:#68717d;font-size:13px;margin-bottom:8px}}
.card strong{{font-size:26px}} section{{padding:24px;margin:18px 0;overflow:auto}}
.data-table,.health{{border-collapse:collapse;width:100%;font-size:13px}}
.data-table th,.data-table td,.health th,.health td{{padding:10px;border-bottom:1px solid #eceff2;text-align:left}}
img{{max-width:100%;height:auto}} .note{{color:#68717d;font-size:13px;line-height:1.5}}
@media(max-width:800px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body><main>
<h1>Pharmaceutical Procurement Intelligence</h1>
<p class="sub">A reproducible decision-intelligence pipeline that ingests public procurement sources, validates and standardizes records, builds analytical marts, and surfaces pricing and supplier-concentration signals for human review.</p>
<div class="cards">{card_html}</div>

<section><h2>Source health</h2>
<table class="health"><thead><tr><th>Source</th><th>Status</th><th>Rows</th><th>Changed this run</th></tr></thead>
<tbody>{health_rows}</tbody></table></section>

<section><h2>Review queue</h2>{table}
<p class="note">Signals prioritize deeper investigation. They do not label a procurement transaction efficient or inefficient.</p></section>

<section><h2>Market footprint</h2><img src="figures/market_value.png"></section>
<section><h2>Supplier footprint</h2><img src="figures/supplier_value.png"></section>
<section><h2>Signal ranking</h2><img src="figures/review_priority.png"></section>

<section><h2>Pipeline</h2>
<p>Sources → raw ingestion → source-level change detection → staging → entity resolution → quality gates → canonical warehouse → analytical marts → signal engine → alerts → executive dashboard.</p>
</section>
</main></body></html>"""
    (OUT / "dashboard.html").write_text(page, encoding="utf-8")

    top = signals.head(8)
    lines = [
        "# Automated Procurement Review Brief",
        "",
        f"Pipeline analyzed **{summary['records_analyzed']:,} transactions** across "
        f"**{summary['countries']} markets** and **{summary['sources_healthy']} healthy source(s)**.",
        "",
        "## Highest-priority review signals",
        "",
    ]
    for _, r in top.iterrows():
        medicine = str(r["product_key"]).split(" | ")[0]
        lines.append(
            f"- **{r['country']} · {medicine}**: review score {r['review_priority_score']:.1f}; "
            f"{int(r['transactions'])} transactions; {int(r['supplier_count'])} suppliers; "
            f"top supplier share {100*r['top_supplier_share']:.1f}%."
        )
    lines += [
        "",
        "## Interpretation rule",
        "",
        "A high score means the combination is commercially material and shows pricing and/or supply concentration patterns worth explaining. It is not evidence of procurement wrongdoing.",
    ]
    (OUT / "automated_review_brief.md").write_text("\n".join(lines), encoding="utf-8")
