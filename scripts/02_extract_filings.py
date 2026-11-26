"""Stream the IRS 2024 e-file zips and extract program text and totals for the study set.

Only mission, program-service and financial-total elements are read. Officer, director, staff,
contractor and Schedule sections (which name people) are never parsed or stored. Email
addresses and phone numbers inside program text are redacted.

python3 -I scripts/02_extract_filings.py          # resumable: skips zips already processed
python3 -I scripts/02_extract_filings.py --keep   # keep zips after extraction (default: delete)
  -> data/interim/filings.jsonl (one line per organization), data/interim/filings_done.txt
"""
import csv, datetime as dt, hashlib, json, re, sys, time, urllib.request, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, INT = ROOT / "data" / "raw" / "irs990", ROOT / "data" / "interim"
ZIPS = RAW / "zips"; ZIPS.mkdir(parents=True, exist_ok=True)
URL = "https://apps.irs.gov/pub/epostcard/990/xml/2024/{}.zip"  # file names use upper-case "A" even when the index says "a"
NS = "{http://www.irs.gov/efile}"
CONTACT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")


def txt(el):
    return CONTACT.sub("[redacted]", " ".join((el.text or "").split())) if el is not None and el.text else None


def num(el):
    try:
        return float(el.text) if el is not None and el.text else None
    except ValueError:
        return None


def first(root, *tags):
    for t in tags:
        el = root.find(f".//{NS}{t}")
        if el is not None and el.text:
            return el
    return None


def parse(xml_bytes, rt):
    root = ET.fromstring(xml_bytes)
    form = root.find(f".//{NS}IRS990EZ" if rt == "990EZ" else f".//{NS}IRS990")
    if form is None:
        return None
    rec = {"programs": []}
    if rt == "990":
        rec["mission"] = txt(first(form, "MissionDesc", "ActivityOrMissionDesc"))
        rec["activity_summary"] = txt(first(form, "ActivityOrMissionDesc"))
        for g in form:
            if g.tag.startswith(f"{NS}ProgSrvcAccomActy"):
                rec["programs"].append({"desc": txt(g.find(f"{NS}Desc")), "expense": num(g.find(f"{NS}ExpenseAmt")),
                                        "grants": num(g.find(f"{NS}GrantAmt")), "revenue": num(g.find(f"{NS}RevenueAmt"))})
        rec["total_revenue"] = num(first(form, "CYTotalRevenueAmt"))
        rec["total_expenses"] = num(first(form, "CYTotalExpensesAmt"))
        tf = form.find(f"{NS}TotalFunctionalExpensesGrp")
        rec["program_expenses"] = num(tf.find(f"{NS}ProgramServicesAmt")) if tf is not None else None
        rec["employees"] = num(first(form, "TotalEmployeeCnt"))
        rec["volunteers"] = num(first(form, "TotalVolunteersCnt"))
        rec["website"] = txt(first(form, "WebsiteAddressTxt"))
    else:
        rec["mission"] = txt(first(form, "PrimaryExemptPurposeTxt"))
        for g in form.findall(f"{NS}ProgramSrvcAccomplishmentGrp"):
            rec["programs"].append({"desc": txt(g.find(f"{NS}DescriptionProgramSrvcAccomTxt")),
                                    "expense": num(g.find(f"{NS}ProgramServiceExpensesAmt")), "grants": num(g.find(f"{NS}GrantsAndAllocationsAmt")),
                                    "revenue": None})
        rec["total_revenue"] = num(first(form, "TotalRevenueAmt"))
        rec["total_expenses"] = num(first(form, "TotalExpensesAmt"))
        rec["program_expenses"] = num(first(form, "TotalProgramServiceExpensesAmt"))
        rec["employees"] = None; rec["volunteers"] = None
        rec["website"] = txt(first(form, "WebsiteAddressTxt"))
    rec["programs"] = [p for p in rec["programs"] if p["desc"]]
    return rec


uni = pd.read_csv(INT / "universe.csv", dtype=str)
done_path = INT / "filings_done.txt"
done = set(done_path.read_text().split()) if done_path.exists() else set()
out = open(INT / "filings.jsonl", "a")
lock_rows = []
for batch, g in uni.groupby("XML_BATCH_ID"):
    if batch in done:
        continue
    zp = ZIPS / f"{batch}.zip"
    if not zp.exists():
        for k in range(4):
            try:
                urllib.request.urlretrieve(URL.format(batch.upper()), zp); break
            except Exception:
                if k == 3:
                    raise
                time.sleep(10 * (k + 1))
    h = hashlib.sha256(zp.read_bytes()).hexdigest()
    want = dict(zip(g.OBJECT_ID, zip(g.EIN, g.RETURN_TYPE, g.TAX_PERIOD)))
    n = 0
    with zipfile.ZipFile(zp) as zf:
        for name in zf.namelist():
            oid = Path(name).name.split("_")[0]
            if oid in want:
                ein, rt, tp = want[oid]
                try:
                    rec = parse(zf.read(name), rt)
                except ET.ParseError:
                    rec = None
                if rec:
                    out.write(json.dumps({"ein": ein, "object_id": oid, "return_type": rt, "tax_period": tp, **rec}) + "\n"); n += 1
    out.flush()
    lock_rows.append({"file": f"irs990/zips/{batch}.zip", "url": URL.format(batch.upper()), "downloaded_utc": dt.datetime.now(dt.timezone.utc).date().isoformat(),
                      "bytes": zp.stat().st_size, "sha256": h})
    with open(done_path, "a") as f:
        f.write(batch + "\n")
    if "--keep" not in sys.argv:
        zp.unlink()
    print(f"{batch}: {n}/{len(g)} filings extracted", flush=True)

lock_path = ROOT / "data" / "sources.lock.csv"
lock = list(csv.DictReader(open(lock_path))) if lock_path.exists() else []
files = {r["file"] for r in lock_rows}
lock = [r for r in lock if r["file"] not in files] + lock_rows
with open(lock_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["file", "url", "downloaded_utc", "bytes", "sha256"], extrasaction="ignore"); w.writeheader(); w.writerows(lock)
