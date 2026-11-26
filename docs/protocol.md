# Protocol: Nonprofit Program DNA

Version 1.0 (2026-11-20). Agents follow this document exactly. Changes get a new version and a
changelog note.

## Question

What do youth-serving nonprofits actually do, beyond their IRS category code? In particular,
how much mentoring and bridging happens inside broader youth, education, recreation and
human-services organizations, and where is it, especially near Project 01's priority
counties?

## Input

One record per organization: its name, IRS category (NTEE), city and state, and the text from
its latest e-filed Form 990 or 990-EZ: the mission statement and up to three or more program
descriptions, each with program expense. Code **only what the text states**.

**Privacy:** filings sometimes name staff, volunteers or participants inside program text.
Never write any person's name in your output. Notes describe the organization's programs in
your own words.

## Tags (one object per organization)

| Field | Values |
|---|---|
| `youth_focus` | `primary` (most activity serves people about 5-24), `partial` (youth are one of several groups served), `none` (no youth-serving activity described), `unclear` (text too thin to tell) |
| `mentoring` | `central` (mentoring relationships are a main activity: mentors matched with youth, "Big Brothers/Big Sisters"-type, mentoring program named as a main program), `component` (mentoring, mentors or role models are mentioned as one part of a broader program), `none` |
| `mentoring_types` | list (empty if `mentoring` is `none`) from `one_to_one`, `group`, `peer` (youth or near-peer mentors), `career_workplace` (professionals, employers, internships with mentors), `school_based`, `online`, `unspecified` |
| `bridging` | `yes` if the organization deliberately connects youth to people, workplaces, colleges or networks beyond their usual circles (career mentors, job shadowing, internships, college visits and advisers, introductions to professionals); `no`; `unclear` |
| `program_types` | list from `sports_recreation`, `academic_tutoring`, `stem`, `arts_culture`, `leadership_civic` (incl. scouting, 4-H clubs, service), `career_workforce`, `college_access`, `camp`, `faith_based`, `health_wellness`, `basic_needs` (food, housing, clothing), `early_childhood_childcare`, `prevention_justice` (delinquency, violence, substance prevention, diversion), `foster_family_support`, `school_support` (PTO, booster club, foundation supporting a school), `facility_grantmaking` (operates a facility or makes grants without describing direct programs), `other` |
| `targets` | list from `low_income`, `at_risk`, `foster_care`, `justice_involved`, `disability`, `girls`, `boys`, `racial_ethnic_minority`, `rural`, `immigrant_refugee`, `lgbtq`, `military_families`, `general` (no particular group stated) |
| `ages` | list from `early_childhood` (0-5), `elementary`, `middle`, `high`, `young_adult` (18-24), `all_youth` (stated as youth/children without ages), `unclear` |
| `youth_served` | integer number of youth (or participants, if clearly youth) the text says were served in the year, else `null` |
| `dose_stated` | `yes` if the text states frequency or duration of participation (e.g., weekly, 10-week program, year-round after-school); else `no` |
| `outcomes_claimed` | list from `academic`, `graduation`, `college`, `career_employment`, `social_emotional`, `health`, `safety_delinquency`, `belonging_relationships`, `none_stated` |
| `evidence_level` | `0` activities only; `1` output counts (number served, events held); `2` outcome claims with numbers (e.g., % improved grades, pre/post results); `3` comparison group, external evaluation or evidence-based model named |
| `notes` | at most 15 words, own words, **no personal names** |

## Quality control

- `scripts/validate.py`: valid JSON, IDs (EINs) match the batch, allowed values, word limits,
  and alignment of notes with each organization's own text (catches shifted rows). It also
  warns when a note repeats a capitalized two-word phrase from the input that is not part of the
  organization's name (a possible personal name); agents rewrite such notes, and
  `scripts/status.py` scans all committed notes for the same pattern.
- Reliability: 4 fixed batches (600 organizations) are tagged a second time, independently, by
  the reference (default) model; agreement and Cohen's kappa per field go to
  `output/tagging_reliability.csv`. The main pass uses Sonnet.
- Before external use, a person checks a sample of tags against the filings, and any candidate
  partner list is reviewed by people who know the communities.
