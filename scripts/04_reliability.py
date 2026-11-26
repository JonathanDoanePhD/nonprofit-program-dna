"""Agreement between the main (Sonnet) and reference (default model) passes on the fixed reliability batches.

python3 -I scripts/04_reliability.py -> output/tagging_reliability.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
C = ROOT / "data" / "coded"
SINGLE = ["youth_focus", "mentoring", "bridging", "dose_stated", "evidence_level"]
LISTS = ["mentoring_types", "program_types", "targets", "ages", "outcomes_claimed"]


def kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = (a == b).mean(); cats = np.union1d(a, b)
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def load(p):
    return {str(e["id"]): e for f in sorted((C / p).glob("batch_*.json")) for e in json.loads(f.read_text())}


M, R = load("main"), load("reference")
ids = sorted(set(M) & set(R))
rows = []
for f in SINGLE:
    a = [str(M[i][f]) for i in ids]; b = [str(R[i][f]) for i in ids]
    rows.append({"field": f, "n": len(ids), "pct_agree": np.mean([x == y for x, y in zip(a, b)]) if ids else np.nan, "kappa": kappa(a, b) if ids else np.nan})
a = [str(M[i]["mentoring"] != "none") for i in ids]; b = [str(R[i]["mentoring"] != "none") for i in ids]
rows.append({"field": "any mentoring (yes/no)", "n": len(ids), "pct_agree": np.mean([x == y for x, y in zip(a, b)]) if ids else np.nan, "kappa": kappa(a, b) if ids else np.nan})
a = [M[i]["evidence_level"] for i in ids]; b = [R[i]["evidence_level"] for i in ids]
rows.append({"field": "evidence_level (within 1)", "n": len(ids), "pct_agree": np.mean([abs(x - y) <= 1 for x, y in zip(a, b)]) if ids else np.nan, "kappa": np.nan})
for f in LISTS:
    jac = [1.0 if not (set(M[i][f]) | set(R[i][f])) else len(set(M[i][f]) & set(R[i][f])) / len(set(M[i][f]) | set(R[i][f])) for i in ids]  # both empty = agree
    rows.append({"field": f"{f} (mean Jaccard)", "n": len(ids), "pct_agree": np.mean(jac) if ids else np.nan, "kappa": np.nan})
    for lab in sorted({x for i in ids for x in M[i][f] + R[i][f]}):
        a = [lab in M[i][f] for i in ids]; b = [lab in R[i][f] for i in ids]
        if sum(a) + sum(b) >= 10:
            rows.append({"field": f"{f}:{lab}", "n": len(ids), "pct_agree": np.mean([x == y for x, y in zip(a, b)]), "kappa": kappa(a, b)})
ys = [(M[i]["youth_served"], R[i]["youth_served"]) for i in ids]
rows.append({"field": "youth_served (same value or both null)", "n": len(ids), "pct_agree": np.mean([x == y for x, y in ys]) if ids else np.nan, "kappa": np.nan})
out = pd.DataFrame(rows); (ROOT / "output").mkdir(exist_ok=True)
out.to_csv(ROOT / "output" / "tagging_reliability.csv", index=False, float_format="%.3f")
print(out.round(2).to_string(index=False))
