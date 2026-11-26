"""Progress and pending batches (done = output exists AND validates). Also scans committed notes for possible names.

python3 -I scripts/status.py [--json]
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B, C = ROOT / "data" / "interim" / "batches" / "org", ROOT / "data" / "coded"


def valid(out):
    return out.exists() and subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "validate.py"), str(out)], capture_output=True).returncode == 0


bs = [b.stem for b in sorted(B.glob("batch_*.jsonl"))]
rel = (C / "reliability_batches.txt").read_text().split() if (C / "reliability_batches.txt").exists() else []
loc = [b for b in bs if json.loads(open(B / f"{b}.jsonl").readline())["stratum"] == "local"]
s = {"main_pending": [b for b in bs if not valid(C / "main" / f"{b}.json")], "main_total": len(bs), "local_batches": loc,
     "reference_pending": [b for b in rel if not valid(C / "reference" / f"{b}.json")], "reference_total": len(rel)}
if "--json" in sys.argv:
    print(json.dumps(s))
else:
    done_local = len([b for b in loc if b not in s["main_pending"]])
    print(f"main      {s['main_total'] - len(s['main_pending'])}/{s['main_total']} batches done (local {done_local}/{len(loc)})")
    print(f"reference {s['reference_total'] - len(s['reference_pending'])}/{s['reference_total']} batches done")
