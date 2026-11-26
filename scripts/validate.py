"""Validate an agent's tagging file against docs/protocol.md. Exit code 0 = valid.

python3 -I scripts/validate.py data/coded/main/batch_0001.json
python3 -I scripts/validate.py data/coded/reference/batch_0003.json
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENUM = {"youth_focus": {"primary", "partial", "none", "unclear"}, "mentoring": {"central", "component", "none"},
        "bridging": {"yes", "no", "unclear"}, "dose_stated": {"yes", "no"}}
LISTS = {
    "mentoring_types": {"one_to_one", "group", "peer", "career_workplace", "school_based", "online", "unspecified"},
    "program_types": {"sports_recreation", "academic_tutoring", "stem", "arts_culture", "leadership_civic", "career_workforce", "college_access",
                      "camp", "faith_based", "health_wellness", "basic_needs", "early_childhood_childcare", "prevention_justice",
                      "foster_family_support", "school_support", "facility_grantmaking", "other"},
    "targets": {"low_income", "at_risk", "foster_care", "justice_involved", "disability", "girls", "boys", "racial_ethnic_minority", "rural",
                "immigrant_refugee", "lgbtq", "military_families", "general"},
    "ages": {"early_childhood", "elementary", "middle", "high", "young_adult", "all_youth", "unclear"},
    "outcomes_claimed": {"academic", "graduation", "college", "career_employment", "social_emotional", "health", "safety_delinquency",
                         "belonging_relationships", "none_stated"},
}
STOPW = set("the a an of and or for in on to with by from at as is are was were be this that these those not no youth "
            "program programs children kids provide provides provided organization services community through their".split())
CAPBI = re.compile(r"\b([A-Z][a-z]+) ([A-Z][a-z]+)\b")


def possible_names(note, rec):
    src = rec["mission"] + " " + " ".join(p["desc"] for p in rec["programs"])
    org = (rec.get("name") or "").lower()
    return [" ".join(m) for m in CAPBI.findall(note or "") if " ".join(m) in src and " ".join(m).lower() not in org]


def alignment(inp, out):
    w = lambda t: {x for x in re.findall(r"[a-z]{4,}", str(t).lower()) if x not in STOPW}
    tx = [w(r["name"] + " " + r["abstract"]) for r in inp]
    wins = n = 0
    for i, r in enumerate(inp):
        rw = w(out.get(r["id"], {}).get("notes", ""))
        if len(rw) < 2:
            continue
        own = len(rw & tx[i]); nb = max(len(rw & tx[j]) for j in (i - 1, i + 1) if 0 <= j < len(inp))
        n += 1; wins += 1 if own > nb else (0.5 if own == nb and own > 0 else 0)
    return wins / n if n else 1.0


def main(path):
    try:
        data = json.loads(Path(path).read_text())
    except Exception as ex:
        print(f"INVALID JSON: {ex}"); return 1
    if not isinstance(data, list):
        print("INVALID: top level must be a list"); return 1
    inp = [json.loads(l) for l in open(ROOT / "data" / "interim" / "batches" / "org" / f"{Path(path).stem}.jsonl")]
    expected = [r["id"] for r in inp]; got = [str(e.get("id")) for e in data]
    errs, warns = [], []
    if sorted(got) != sorted(expected):
        m, x = set(expected) - set(got), set(got) - set(expected)
        errs.append(f"id mismatch: missing {sorted(m)[:5]} ({len(m)}), extra {sorted(x)[:5]} ({len(x)}), dupes {len(got) - len(set(got))}")
    byid = {r["id"]: r for r in inp}
    for i, e in enumerate(data):
        for k, allowed in ENUM.items():
            if e.get(k) not in allowed:
                errs.append(f"[{i}] bad {k}={e.get(k)!r}")
        for k, allowed in LISTS.items():
            v = e.get(k)
            if not isinstance(v, list) or any(t not in allowed for t in v):
                errs.append(f"[{i}] bad {k}={v!r}")
        if e.get("mentoring") == "none" and e.get("mentoring_types"):
            errs.append(f"[{i}] mentoring_types must be empty when mentoring is none")
        if e.get("mentoring") in ("central", "component") and not e.get("mentoring_types"):
            errs.append(f"[{i}] mentoring_types needs at least one value (use unspecified)")
        if not isinstance(e.get("program_types"), list) or not e.get("program_types"):
            errs.append(f"[{i}] program_types needs at least one value")
        ys = e.get("youth_served")
        if ys is not None and (not isinstance(ys, int) or isinstance(ys, bool) or ys < 0):
            errs.append(f"[{i}] youth_served must be a non-negative int or null")
        if e.get("evidence_level") not in (0, 1, 2, 3):
            errs.append(f"[{i}] evidence_level must be 0-3")
        if len(str(e.get("notes") or "").split()) > 20:
            errs.append(f"[{i}] notes too long")
        if str(e.get("id")) in byid:
            pn = possible_names(e.get("notes"), byid[str(e["id"])])
            if pn:
                errs.append(f"[{i}] notes may contain a personal name {pn}: rewrite the note without names")
    if not errs:
        a = alignment(inp, {str(e["id"]): e for e in data})
        if a < 0.75:
            errs.append(f"notes do not match their records (alignment {a:.2f} < 0.75): tags look shifted. "
                        "Rebuild the file by matching each record's id to its own text.")
    if errs:
        print("INVALID:\n" + "\n".join(errs[:40])); return 1
    print(f"VALID: {len(data)} records"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
