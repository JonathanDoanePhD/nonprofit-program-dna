# How to resume the pipeline

Run from this project folder.

1. **Rebuild inputs if the container is new** (`data/raw/` and `data/interim/` are not committed):
   `python3 -I scripts/fetch_data.py .`, then `scripts/01_select_universe.py`,
   `scripts/02_extract_filings.py` and `scripts/03_make_batches.py`. Selection and batches are
   deterministic for a given BMF and index download; check `data/sources.lock.csv` hashes.
2. **Pending:** `python3 -I scripts/status.py --json`. The `local_batches` list (priority
   areas) comes first; national batches are in random order, so any prefix is a random sample.
3. **Tag:** `scripts/workflows/tag.js` with
   `args: {"main": [<pending main batches, local first>], "reference": [<pending reference batches>]}` (main uses Sonnet; reference the default model).
   Use `{"pass": "reference", "batch": ...}` (default model) for `data/coded/reliability_batches.txt`.
4. Then `scripts/04_reliability.py` and `scripts/05_analysis.py`. Commit `data/coded/` and
   `output/` after each wave (never `data/raw/` or `data/interim/`).
