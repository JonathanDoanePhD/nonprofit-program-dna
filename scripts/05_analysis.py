"""Nonprofit Program DNA: hidden mentoring, local supply map, candidate partners, program mix.

python3 -I scripts/05_analysis.py   (works with partial tags)
Outputs (output/):
  orgs_tagged.csv              one row per tagged organization: category, place, finances, tags (no filing text)
  hidden_mentoring.csv         national random sample: share with mentoring by IRS category, vs. IRS mentoring codes and a keyword search
  program_mix.csv              program types, outcomes claimed, evidence level, dose (national sample and local set)
  priority_county_supply.csv   per priority county: youth/mentoring/bridging orgs in the county and in county + neighbors, per 10k children
  candidate_partners.csv       organizations in or next to priority counties that mentor or bridge (FOR HUMAN REVIEW)
  dna_summary.json             headline numbers
  fig_hidden_mentoring.png, fig_priority_supply.png
"""
import json, re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INT, C, OUT = ROOT / "data" / "interim", ROOT / "data" / "coded", ROOT / "output"
OUT.mkdir(exist_ok=True)
summary = {}

uni = pd.read_csv(INT / "universe.csv", dtype=str)
fil = {json.loads(l)["ein"]: json.loads(l) for l in open(INT / "filings.jsonl")}
tags = {str(e["id"]): e for f in sorted((C / "main").glob("batch_*.json")) for e in json.loads(f.read_text())}
batch_of = {}
for f in sorted((INT / "batches" / "org").glob("batch_*.jsonl")):
    for l in open(f):
        batch_of[json.loads(l)["id"]] = f.stem

d = uni[uni.EIN.isin(tags)].copy()
for k in ["total_revenue", "total_expenses", "program_expenses", "employees", "volunteers"]:
    d[k] = d.EIN.map(lambda e: fil[e].get(k))
TAGF = ["youth_focus", "mentoring", "mentoring_types", "bridging", "program_types", "targets", "ages", "youth_served", "dose_stated",
        "outcomes_claimed", "evidence_level"]
for f in TAGF:
    d[f] = d.EIN.map(lambda e: tags[e][f])
d["batch"] = d.EIN.map(batch_of)
d["ntee3"] = d.NTEE_CD.fillna("").str[:3]
d["irs_mentoring_code"] = d.ntee3.isin(["O30", "O31"])
text = d.EIN.map(lambda e: ((fil[e].get("mission") or "") + " " + " ".join(p["desc"] or "" for p in fil[e]["programs"])).lower())
d["keyword_mentor"] = text.str.contains(r"\bmentor", regex=True)
d["any_mentoring"] = d.mentoring != "none"
d["youth_serving"] = d.youth_focus.isin(["primary", "partial"])
listcols = ["mentoring_types", "program_types", "targets", "ages", "outcomes_claimed"]
o = d.copy()
for c in listcols:
    o[c] = o[c].apply(lambda x: ";".join(x))
o.drop(columns=["XML_BATCH_ID", "OBJECT_ID"]).to_csv(OUT / "orgs_tagged.csv", index=False)
summary["tagged"] = {"organizations": int(len(d)), "local": int((d.stratum == "local").sum()), "national": int((d.stratum == "national").sum())}


def share_ci(x):
    x = np.asarray(x, dtype=float); n = len(x)
    if n == 0:
        return np.nan, np.nan, np.nan
    p = x.mean(); se = np.sqrt(p * (1 - p) / n)
    return p, max(0, p - 1.96 * se), min(1, p + 1.96 * se)


# ---------- hidden mentoring (national random sample of youth development orgs) ----------
nat = d[d.stratum == "national"]
rows = []
groups = [("All youth development (O) orgs", nat), ("IRS-coded mentoring (O30/O31)", nat[nat.irs_mentoring_code]),
          ("Other youth development orgs", nat[~nat.irs_mentoring_code])]
for sub, g in nat.groupby(nat.ntee3.where(nat.ntee3.isin(["O20", "O21", "O22", "O23", "O30", "O31", "O40", "O41", "O42", "O43", "O50", "O51", "O52", "O53", "O54", "O55"]), "O other")):
    groups.append((f"NTEE {sub}", g))
for name, g in groups:
    p, lo, hi = share_ci(g.any_mentoring)
    rows.append({"group": name, "orgs": len(g), "share_any_mentoring": p, "ci_low": lo, "ci_high": hi,
                 "share_central": (g.mentoring == "central").mean() if len(g) else np.nan,
                 "share_bridging": (g.bridging == "yes").mean() if len(g) else np.nan,
                 "share_keyword_mentor": g.keyword_mentor.mean() if len(g) else np.nan})
hm = pd.DataFrame(rows); hm.to_csv(OUT / "hidden_mentoring.csv", index=False, float_format="%.4f")
if len(nat):
    pop = (uni.stratum == "national").sum()  # national study set with e-file
    p, lo, hi = share_ci(nat.any_mentoring)
    coded = nat.irs_mentoring_code.mean()
    summary["hidden_mentoring"] = {
        "national_sample_orgs": int(len(nat)), "share_any_mentoring": p, "ci": [lo, hi],
        "share_central": float((nat.mentoring == "central").mean()), "share_bridging": float((nat.bridging == "yes").mean()),
        "share_irs_mentoring_code": float(coded), "est_orgs_with_mentoring_in_efile_O_universe": [round(lo * pop), round(p * pop), round(hi * pop)],
        "ratio_tagged_to_irs_coded": float(p / coded) if coded else None,
        "share_of_mentoring_orgs_without_irs_code": float((nat.any_mentoring & ~nat.irs_mentoring_code).sum() / max(1, nat.any_mentoring.sum())),
        "keyword_mentor_share": float(nat.keyword_mentor.mean()),
        "keyword_vs_tag_agreement": float((nat.keyword_mentor == nat.any_mentoring).mean()),
    }

# ---------- program mix ----------
pm = []
for st, g in d.groupby("stratum"):
    ys = g[g.youth_serving]
    for c in ["program_types", "outcomes_claimed", "targets", "mentoring_types"]:
        for v, gg in ys.explode(c).groupby(c):
            pm.append({"stratum": st, "field": c, "value": v, "orgs": gg.EIN.nunique(), "share_of_youth_serving": gg.EIN.nunique() / len(ys)})
    for v, gg in ys.groupby("evidence_level"):
        pm.append({"stratum": st, "field": "evidence_level", "value": v, "orgs": len(gg), "share_of_youth_serving": len(gg) / len(ys)})
    pm.append({"stratum": st, "field": "dose_stated", "value": "yes", "orgs": int((ys.dose_stated == "yes").sum()),
               "share_of_youth_serving": (ys.dose_stated == "yes").mean()})
pd.DataFrame(pm).to_csv(OUT / "program_mix.csv", index=False, float_format="%.4f")

# ---------- priority-county supply ----------
ct = pd.read_csv(ROOT / "data" / "external" / "county_table_project01.csv", dtype={"fips": str})
ct["fips"] = ct.fips.str.zfill(5)
pri = ct[ct.priority_flag == True][["fips", "county_name", "state", "children_0_17_acs2022", "has_dedicated_mentoring_org"]]
adj = pd.read_csv(ROOT / "data" / "raw" / "census" / "county_adjacency2023.txt", sep="|", dtype=str)
nbrs = adj.groupby("County GEOID")["Neighbor GEOID"].apply(set).to_dict()
loc = d[d.stratum == "local"]
kids = ct.set_index("fips").children_0_17_acs2022
srows = []
for r in pri.itertuples():
    area = nbrs.get(r.fips, {r.fips}) | {r.fips}
    for scope, cs in [("county", {r.fips}), ("county_plus_neighbors", area)]:
        g = loc[loc.county_fips.isin(cs)]
        k = kids.reindex(list(cs)).sum()
        srows.append({"fips": r.fips, "county_name": r.county_name, "state": r.state, "scope": scope, "children": k,
                      "youth_serving_orgs": int(g.youth_serving.sum()), "mentoring_orgs": int((g.youth_serving & g.any_mentoring).sum()),
                      "mentoring_central_orgs": int((g.mentoring == "central").sum()), "bridging_orgs": int((g.youth_serving & (g.bridging == "yes")).sum()),
                      "irs_coded_mentoring_orgs": int(g.irs_mentoring_code.sum()),
                      "mentoring_orgs_per_10k_children": (g.youth_serving & g.any_mentoring).sum() / k * 1e4 if k else np.nan,
                      "program_expenses_mentoring_orgs": float(g[g.youth_serving & g.any_mentoring].program_expenses.fillna(0).sum())})
sp = pd.DataFrame(srows); sp.to_csv(OUT / "priority_county_supply.csv", index=False, float_format="%.3f")
if len(loc):
    cty = sp[sp.scope == "county"]; area = sp[sp.scope == "county_plus_neighbors"]
    summary["priority_supply"] = {
        "priority_counties": int(len(cty)),
        "with_any_youth_serving_org_in_county": int((cty.youth_serving_orgs > 0).sum()),
        "with_any_mentoring_org_in_county": int((cty.mentoring_orgs > 0).sum()),
        "with_any_mentoring_org_in_county_or_neighbor": int((area.mentoring_orgs > 0).sum()),
        "with_irs_coded_mentoring_org_in_county": int((cty.irs_coded_mentoring_orgs > 0).sum()),
        "median_mentoring_orgs_per_10k_children_county_plus_neighbors": float(area.mentoring_orgs_per_10k_children.median()),
        "local_set_tagged_share": float(len(loc) / max(1, (uni.stratum == "local").sum())),
    }

# ---------- candidate partners (human review required) ----------
cand = loc[loc.youth_serving & (loc.any_mentoring | (loc.bridging == "yes"))].copy()
cand["in_priority_county"] = cand.in_priority_county.astype(str) == "True"
cand = cand.assign(mentoring_types=cand.mentoring_types.apply(";".join), program_types=cand.program_types.apply(";".join),
                   targets=cand.targets.apply(";".join))
cand = cand[["EIN", "NAME", "CITY", "STATE", "county_fips", "in_priority_county", "NTEE_CD", "total_revenue", "program_expenses", "volunteers",
             "youth_focus", "mentoring", "mentoring_types", "bridging", "program_types", "targets", "youth_served", "evidence_level"]]
cand.sort_values(["in_priority_county", "mentoring", "total_revenue"], ascending=[False, True, False]).to_csv(OUT / "candidate_partners.csv", index=False)
summary["candidate_partners"] = {"organizations": int(len(cand)), "in_priority_counties": int(cand.in_priority_county.sum())}

# ---------- figures ----------
if len(nat) >= 50:
    g = hm[hm.group.str.startswith("NTEE")].query("orgs >= 25").sort_values("share_any_mentoring")
    fig, ax = plt.subplots(figsize=(9.5, 0.42 * len(g) + 2), dpi=100)
    ax.barh(g.group, g.share_any_mentoring * 100, xerr=[(g.share_any_mentoring - g.ci_low) * 100, (g.ci_high - g.share_any_mentoring) * 100],
            color=["#eb6834" if x in ("NTEE O30", "NTEE O31") else "#2a78d6" for x in g.group], ecolor="#52514e", capsize=2)
    for y, (s, n) in enumerate(zip(g.share_any_mentoring, g.orgs)):
        ax.text(1, y, f"n={n}", va="center", fontsize=8, color="white" if s > 0.08 else "#0b0b0b")
    ax.set_xlabel("Share of organizations whose filing describes mentoring (central or component), %")
    ax.set_title("Mentoring hides inside youth organizations of every IRS category", loc="left", fontsize=12)
    fig.text(0.01, 0.01, "Youth development (NTEE O) organizations outside the local set with a 2024 Form 990/990-EZ (10,818); orange = IRS mentoring codes. "
             "AI-agent tags; verify before external use.", fontsize=7.3, color="#52514e")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(OUT / "fig_hidden_mentoring.png", dpi=150); plt.close(fig)
if len(loc):
    a = sp[sp.scope == "county_plus_neighbors"].copy()
    c1 = sp[sp.scope == "county"].set_index("fips")
    a["in_county"] = a.fips.map(c1.mentoring_orgs)
    a = a.sort_values("mentoring_orgs")
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=100)
    bins = [0, 1, 2, 3, 5, 10, 20, 1000]; labs = ["0", "1", "2", "3-4", "5-9", "10-19", "20+"]
    h1 = pd.cut(c1.mentoring_orgs, bins, right=False, labels=labs).value_counts().reindex(labs)
    h2 = pd.cut(a.mentoring_orgs, bins, right=False, labels=labs).value_counts().reindex(labs)
    x = np.arange(len(labs))
    ax.bar(x - 0.2, h1.values, 0.4, color="#eb6834", label="In the county")
    ax.bar(x + 0.2, h2.values, 0.4, color="#2a78d6", label="In the county or a neighboring county")
    ax.set_xticks(x, labs); ax.set_xlabel("Organizations whose filings describe youth mentoring"); ax.set_ylabel("Priority counties")
    ax.legend(frameon=False); ax.set_title("Mentoring supply around Project 01's 124 priority counties", loc="left", fontsize=12)
    fig.text(0.01, 0.01, "Organizations filing a 2024 Form 990/990-EZ (small 990-N filers have no program text). AI-agent tags; verify before external use.",
             fontsize=7.3, color="#52514e")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(OUT / "fig_priority_supply.png", dpi=150); plt.close(fig)

(OUT / "dna_summary.json").write_text(json.dumps(summary, indent=2, default=float))
print(json.dumps(summary, indent=1, default=float))
