# 10 - Nonprofit Program DNA

**Question:** What do youth-serving nonprofits actually do, beyond their IRS category? How
much mentoring and bridging happens inside broader youth, education, recreation and
human-services organizations, and where is it, especially in and around Project 01's
priority counties?

**Status:** first pass complete (2026-11-20). All 15,473 organizations are tagged, and the
reliability and analysis outputs are built. Next: a person spot-checks a sample of tags, and
people who know the communities review the candidate partner list (see Next steps).

> **Exploratory, AI-assisted research.** Tags come from Claude agents reading Form 990
> program text under [docs/protocol.md](docs/protocol.md), with validation and an independent
> reference-model pass. Filings describe what organizations say they do. Before external use,
> a person checks a sample of tags, and people who know the communities review any partner
> list.

## Key findings

1. **Mentoring is about five times as common as the IRS codes show.**
   - Of 10,818 youth development organizations filing a full or short-form 990
     (`hidden_mentoring.csv`), **12.7% (1,372) describe mentoring** in their program text.
     Only **2.3% (254)** carry an IRS mentoring code (O30/O31).
   - **89% of the organizations that mentor have no mentoring code.** They are mostly general
     youth development programs (O50: 15% mentor), youth centers and clubs, and leadership,
     citizenship and religious youth groups.
   - The code is also imperfect from the other side: only 57% of organizations coded as
     mentoring describe mentoring in their latest filing.
2. **A simple keyword finds most of it.** Searching filings for "mentor" agrees with the agent
   tags for 98% of organizations. So a cheap yearly keyword screen can track mentoring supply,
   and agents add the detail: central or component role, type, bridging and evidence.
3. **Filings rarely say what kind of mentoring, or how much.** Among youth-serving
   organizations, mentoring type is unspecified for 10%, and only 2% name one-to-one, 1% group
   and 1% career or workplace mentoring. Just 11% state any dose (how often or how long).
4. **Mentoring and bridging travel together.** 21% of organizations that mentor also connect
   youth to people, colleges or workplaces beyond their usual circles, against 2% of those
   that do not.
5. **Evidence is thin.** 81% of youth-serving filings describe activities only and 17% give
   counts served. **Only 1.3% report numbered outcomes or name an evaluation or
   evidence-based model**, and 76% claim no outcome at all. This matches the gap Project 08
   found in the research literature.
6. **Priority counties are close to mentoring deserts** (`priority_county_supply.csv`).
   - In or next to Project 01's 124 priority counties, every education, recreation,
     human-services and youth organization was tagged (4,655).
   - Only **4 of 124 priority counties** have an organization that files a 990 or 990-EZ and
     describes youth mentoring within the county. **62** have one in the county or a
     neighboring county.
   - 43 have no youth-serving organization filing a full or short-form return at all.
   - None has an organization with an IRS mentoring code.
   - Small groups (990-N filers), churches, schools and informal mentors are not visible here,
     so local knowledge must fill this in.
7. **Candidate partners:** 136 organizations in or next to priority counties mentor or bridge
   (5 inside a priority county) (`candidate_partners.csv`). **This list is a starting point
   for review by people who know these communities, not a recommendation or an endorsement.**

## Reliability

A reference model tagged 600 organizations (4 fixed batches) independently of the main Sonnet
pass (`output/tagging_reliability.csv`). Kappa (agreement beyond chance; 1 is perfect):

| Field | Kappa |
|---|---|
| Mentoring (central, component or none) | 0.96 |
| Any mentoring, yes or no | 1.00 |
| Evidence level | 0.92 |
| Youth focus | 0.91 |
| Dose stated | 0.76 |
| Bridging | 0.60 (rare tag; treat counts as approximate) |

List fields overlap well: mean Jaccard 0.99 for mentoring types, 0.81 for program types, 0.87
for target groups and 0.73 for ages.

## Data

| Source | What |
|---|---|
| IRS Exempt Organizations Business Master File | Every exempt organization's IRS category (NTEE), location and income |
| IRS Form 990 e-file data (2024 release) | Latest Form 990 / 990-EZ per organization: mission, program descriptions and program expenses, revenue, expenses, staff and volunteer counts |
| Census | ZIP-to-county file, county adjacency |
| Project 01 | 124 priority counties |

**Study set:** 15,873 organizations with a 2024 e-filed 990 or 990-EZ (15,473 with usable
program text). That covers every youth, education, recreation or human-services organization
(IRS categories O, B, N, P) in a priority county or a county next to one (4,806), plus every
other youth development organization (category O) nationally (11,067). Organizations under
$50K in income file the 990-N postcard, which has no program text, so they are not in the
study set (`output/universe_counts.csv`).

**Privacy:** only mission, program-description and financial-total elements are parsed.
Officer, director, staff and contractor sections are never read. Emails and phone numbers are
redacted. Agents never write personal names, and a validator check rejects notes that repeat
name-like phrases from the input. Filing text stays in `data/interim/`, which is not
committed.

## Rebuild

```bash
python3 -I scripts/fetch_data.py .
python3 -I scripts/01_select_universe.py
python3 -I scripts/02_extract_filings.py     # streams ~2.8 GB of IRS zips, one at a time, deleting each
python3 -I scripts/03_make_batches.py
# tagging: see RESUME.md
```

## Outputs

| File | What |
|---|---|
| `output/universe_counts.csv` | Organizations per stratum and IRS category, and how many have an e-filed return |
| `output/orgs_tagged.csv` | One row per organization: category, place, finances (revenue, program expenses, staff, volunteers) and tags. No filing text |
| `output/hidden_mentoring.csv` | Share with mentoring by IRS category, with 95% intervals, central share, bridging share and keyword share |
| `output/program_mix.csv` | Program types, outcomes claimed, target groups, mentoring types, evidence level and dose, for local and national organizations |
| `output/priority_county_supply.csv` | Per priority county, in the county and with neighbors: youth-serving, mentoring and bridging organizations, per 10k children |
| `output/candidate_partners.csv` | Organizations in or next to priority counties that mentor or bridge. **For human review only** |
| `output/tagging_reliability.csv` | Main vs. reference agreement |
| `output/dna_summary.json` | Headline numbers |
| `output/fig_hidden_mentoring.png`, `fig_priority_supply.png` | Figures |
| `data/coded/main/`, `data/coded/reference/` | All agent tags (no filing text; short paraphrased notes; no personal names) |

## Caveats

- **Filings describe what organizations say they do,** in a few sentences, for one year.
  Mentoring that is not mentioned is invisible, and stated aims are not results.
- **Only e-filed 990 and 990-EZ filers are covered.** Organizations under $50K file the 990-N
  postcard, which has no program text. Churches and schools often file nothing. The supply
  counts are therefore a floor, especially in small rural counties.
- **Location is the filing address,** not every place an organization serves.
- **The national set is nearly complete:** 10,818 of the 11,067 youth development e-filers;
  the rest had too little text to tag. Its shares are close to a census, not a sample.
- **Tags come from AI models,** and reliability is model-to-model.
- **Organization names appear in outputs** because they are public filers. No personal names
  are stored, and filing text stays in `data/interim/`, which is not committed.

## Next steps

- **Human spot-check:** a person reviews 50 random organizations (stratified by mentoring tag)
  against their filings.
- **Community review of `candidate_partners.csv`:** people who know each priority area check
  the list, add organizations that don't file (churches, schools, informal programs), and decide
  whether any outreach is appropriate. This analysis makes no recommendation about any
  organization.
- **Trend:** repeat with the 2025 and 2026 e-file releases, using the keyword screen to track
  change cheaply.
- **Link to Project 09:** map national mentoring intermediaries' local affiliates (by EIN or
  group-exemption number) to see where federal mentoring money is actually spent.

## License, citation and data terms

- **Code:** MIT (proposed; see `LICENSE`). **Outputs:** CC BY 4.0 (proposed), subject to the source terms below.
- **Cite this project as:** JonathanDoanePhD (2026). *Nonprofit Program DNA*. https://github.com/JonathanDoanePhD/nonprofit-program-dna
- **Data sources and terms** (from `data/sources.csv`; recorded versions and checksums in `data/sources.lock.csv`):

| Source | Terms |
|---|---|
| IRS Form 990 e-file index (returns processed in 2023) | Public domain (U.S. government work); e-filed returns are public records |
| IRS Form 990 e-file index (returns processed in 2024) | Public domain (U.S. government work); e-filed returns are public records |
| IRS Exempt Organizations Business Master File (region 1) | Public domain (U.S. government work) |
| IRS Exempt Organizations Business Master File (region 2) | Public domain (U.S. government work) |
| IRS Exempt Organizations Business Master File (region 3) | Public domain (U.S. government work) |
| IRS Exempt Organizations Business Master File (region 4) | Public domain (U.S. government work) |
| U.S. Census Bureau 2020 ZCTA-to-county relationship file | Public domain (U.S. government work) |
| U.S. Census Bureau county adjacency file 2023 | Public domain (U.S. government work) |

Built with AI assistance (Claude). Exploratory research: every statistic needs checking against its original source
before it appears in funder reports, grant applications or public material.

## Before public release

- [ ] Every statistic in this README and in `output/` is checked against its original source.
- [ ] A person spot-checks a sample of tags against the filings.
- [ ] candidate_partners.csv is withheld from this repository until people who know the communities review it; the script that builds it is included.
- [ ] The owner confirms the license choice above.

Withheld from this repository until reviewed: `output/candidate_partners.csv`.
