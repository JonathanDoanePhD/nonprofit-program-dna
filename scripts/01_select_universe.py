"""Select the organizations to study and locate their latest e-filed return.

Universe (IRS Business Master File, NTEE codes):
  - local:    youth development (O), education (B), recreation/sports (N) and human services (P)
              organizations in Project 01's 124 priority counties or a county adjacent to one
  - national: all other youth development (O) organizations, shuffled with a fixed seed so any
              prefix of the batch order is a random sample
Only organizations with a Form 990 or 990-EZ in the IRS 2024 e-file index have program text
(990-N filers do not), so the study set is the universe joined to that index.

python3 -I scripts/01_select_universe.py -> data/interim/universe.csv, output/universe_counts.csv
"""
import glob
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, INT, OUT = ROOT / "data" / "raw", ROOT / "data" / "interim", ROOT / "output"
INT.mkdir(parents=True, exist_ok=True); OUT.mkdir(exist_ok=True)
SEED = 20261120

eo = pd.concat([pd.read_csv(f, dtype=str, usecols=["EIN", "NAME", "CITY", "STATE", "ZIP", "NTEE_CD", "INCOME_AMT", "REVENUE_AMT"])
                for f in sorted(glob.glob(str(RAW / "bmf" / "eo*.csv")))]).drop_duplicates("EIN")
eo["ntee_major"] = eo.NTEE_CD.fillna("").str[:1]
z = pd.read_csv(RAW / "census" / "tab20_zcta520_county20_natl.txt", sep="|", dtype=str, encoding="utf-8-sig")
z = z[z.GEOID_ZCTA5_20.fillna("") != ""]; z["land"] = pd.to_numeric(z.AREALAND_PART, errors="coerce")
z2c = z.sort_values("land", ascending=False).drop_duplicates("GEOID_ZCTA5_20").set_index("GEOID_ZCTA5_20").GEOID_COUNTY_20
eo["county_fips"] = eo.ZIP.fillna("").str[:5].map(z2c)

ct = pd.read_csv(ROOT / "data" / "external" / "county_table_project01.csv", dtype={"fips": str})
ct["fips"] = ct.fips.str.zfill(5)
pri = set(ct[ct.priority_flag == True].fips)
adj = pd.read_csv(RAW / "census" / "county_adjacency2023.txt", sep="|", dtype=str)
near = pri | set(adj[adj["County GEOID"].isin(pri)]["Neighbor GEOID"])

local = eo[eo.ntee_major.isin(["O", "B", "N", "P"]) & eo.county_fips.isin(near)].assign(stratum="local")
national = eo[(eo.ntee_major == "O") & ~eo.EIN.isin(local.EIN)].assign(stratum="national")
uni = pd.concat([local, national])
uni["in_priority_county"] = uni.county_fips.isin(pri)

idx = pd.read_csv(RAW / "irs990" / "index_2024.csv", dtype=str)
idx = idx[idx.RETURN_TYPE.isin(["990", "990EZ"])].sort_values(["TAX_PERIOD", "SUB_DATE"]).drop_duplicates("EIN", keep="last")
uni = uni.merge(idx[["EIN", "RETURN_TYPE", "TAX_PERIOD", "OBJECT_ID", "XML_BATCH_ID"]], on="EIN", how="left")
uni["has_efile"] = uni.OBJECT_ID.notna()

counts = uni.groupby(["stratum", "ntee_major"]).agg(orgs=("EIN", "size"), with_efile=("has_efile", "sum")).reset_index()
counts.to_csv(OUT / "universe_counts.csv", index=False)
print(counts.to_string(index=False))

study = uni[uni.has_efile].copy()
# batch order: local first (sorted by county), then national in a fixed random order
study["order"] = 0.0
loc = study.stratum == "local"
study.loc[loc, "order"] = study[loc].county_fips.rank(method="first") / 1e6
study.loc[~loc, "order"] = 1 + study[~loc].sample(frac=1, random_state=SEED).assign(r=range((~loc).sum())).r.reindex(study[~loc].index) / 1e6
study = study.sort_values("order").drop(columns="order")
study.to_csv(INT / "universe.csv", index=False)
print(f"study set: {len(study):,} organizations ({loc.sum():,} local, {(~loc).sum():,} national)")
