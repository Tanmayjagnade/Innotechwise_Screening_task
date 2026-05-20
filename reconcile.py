import csv
import os
from typing import Dict, List

from openai import OpenAI

ERP_FEED_PATH = "data/erp_feed.csv"
FLAG_THRESHOLD = 0.05  # 5% deviation triggers a flag


def _load_erp_data(producer_id: str, month: str) -> Dict[str, float]:
    erp: Dict[str, float] = {}
    if not os.path.exists(ERP_FEED_PATH):
        return erp
    with open(ERP_FEED_PATH, newline="") as f:
        for row in csv.DictReader(f):
            if row["producer_id"] == producer_id and row["month"] == month:
                erp[row["category"]] = float(row["procured_kg"])
    return erp


def _build_reconciliation(declared: Dict[str, float], erp: Dict[str, float]) -> List[dict]:
    entries = []
    for category in sorted(set(declared) | set(erp)):
        d_qty = declared.get(category, 0.0)
        e_qty = erp.get(category, 0.0)

        if e_qty > 0:
            diff_pct = abs(d_qty - e_qty) / e_qty
        elif d_qty > 0:
            diff_pct = 1.0
        else:
            diff_pct = 0.0

        entries.append({
            "category": category,
            "declared_kg": d_qty,
            "procured_kg": e_qty,
            "difference_kg": round(d_qty - e_qty, 2),
            "difference_pct": round(diff_pct * 100, 2),
            "flagged": diff_pct > FLAG_THRESHOLD,
        })
    return entries


def _generate_narrative(producer_id: str, month: str, entries: List[dict]) -> str:
    lines = [
        f"  - {e['category']}: declared {e['declared_kg']} kg, procured {e['procured_kg']} kg, "
        f"deviation {e['difference_pct']}%{' [FLAGGED]' if e['flagged'] else ''}"
        for e in entries
    ]
    rec_block = "\n".join(lines)

    prompt = (
        f"You are a compliance analyst reviewing EPR (Extended Producer Responsibility) data for India.\n\n"
        f"Reconciliation for producer {producer_id}, month {month}:\n{rec_block}\n\n"
        f"Write 3–5 sentences that:\n"
        f"1. State the overall compliance status.\n"
        f"2. Explain any flagged categories (>5% deviation) in plain English.\n"
        f"3. Give one concrete recommended action.\n\n"
        f"Do NOT restate raw numbers verbatim — your role is narrative. Be concise and professional."
    )

    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    message = client.chat.completions.create(
        model="llama3.2:1b",
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.choices[0].message.content.strip()


def reconcile_with_erp(declaration: dict) -> dict:
    declared = declaration["declared_quantities_kg"]
    erp = _load_erp_data(declaration["producer_id"], declaration["month"])

    entries = _build_reconciliation(declared, erp)
    flags = [e for e in entries if e["flagged"]]
    narrative = _generate_narrative(declaration["producer_id"], declaration["month"], entries)

    return {
        "producer_id": declaration["producer_id"],
        "month": declaration["month"],
        "reconciliation": entries,
        "flags": flags,
        "narrative": narrative,
    }
