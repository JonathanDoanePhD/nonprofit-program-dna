"""Build agent input batches from extracted filings, in the universe's priority order.

python3 -I scripts/03_make_batches.py
  -> data/interim/batches/org/batch_NNNN.jsonl (150 organizations each; local first, then a random national order)
  -> data/coded/reliability_batches.txt (4 fixed batches for a reference-model pass: 2 local, 2 national)
"""
import json, random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INT = ROOT / "data" / "interim"
B = INT / "batches" / "org"; B.mkdir(parents=True, exist_ok=True)
SIZE, SEED = 150, 20261120

uni = pd.read_csv(INT / "universe.csv", dtype=str)
fil = {}
for l in open(INT / "filings.jsonl"):
    r = json.loads(l); fil[r["ein"]] = r
recs = []
for u in uni.itertuples():
    f = fil.get(u.EIN)
    if not f:
        continue
    progs = [{"desc": p["desc"], "expense": p["expense"]} for p in f["programs"] if p.get("desc")]
    text_len = len(f.get("mission") or "") + sum(len(p["desc"]) for p in progs)
    if text_len < 30:
        continue
    recs.append({"id": u.EIN, "name": u.NAME, "ntee": u.NTEE_CD, "city": u.CITY, "state": u.STATE, "stratum": u.stratum,
                 "mission": f.get("mission") or "", "programs": progs, "title": u.NAME,
                 "abstract": (f.get("mission") or "") + " " + " ".join(p["desc"] for p in progs)})
for f_ in B.glob("batch_*.jsonl"):
    f_.unlink()
n = 0
for k in range(0, len(recs), SIZE):
    n += 1
    with open(B / f"batch_{n:04d}.jsonl", "w") as fh:
        for r in recs[k:k + SIZE]:
            fh.write(json.dumps(r) + "\n")
loc_batches = [i + 1 for i in range(n) if json.loads(open(B / f"batch_{i + 1:04d}.jsonl").readline())["stratum"] == "local"]
nat_batches = [i for i in range(1, n + 1) if i not in loc_batches]
rng = random.Random(SEED)
rel = sorted(rng.sample(loc_batches[:-1], 2) + rng.sample(nat_batches[:20], 2))  # national from early (sample) batches
C = ROOT / "data" / "coded"; C.mkdir(parents=True, exist_ok=True)
(C / "reliability_batches.txt").write_text("\n".join(f"batch_{i:04d}" for i in rel) + "\n")
print(f"{len(recs):,} organizations with program text in {n} batches ({len(loc_batches)} local); reliability batches {rel}")
