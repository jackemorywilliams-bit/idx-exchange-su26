# IDX Exchange · Data Analyst Internship

Real estate market intelligence through MLS analytics.
Summer 2026 · Python · pandas · Tableau · CoreLogic Trestle API

## About

A 12-week data analyst internship at IDX Exchange, a real estate technology company, focused on turning raw CRMLS (California Regional Multiple Listing Service) data into market intelligence. The pipeline moves raw MLS pulls → Python extraction and consolidation → two canonical datasets → Tableau Public dashboards.

> No proprietary MLS data, API credentials, or client records are stored in this repository. Raw CSVs are produced and kept **local only**.

## Objectives

- Pull **listings** and **sold** MLS records from the CoreLogic Trestle API.
- Maintain two canonical, ever-growing datasets — listings (everything on the market) and sold (only closed transactions) — as **separate pipelines**.
- Filter and standardize the data for analysis.
- Build and publish market dashboards on Tableau Public.

## Repository structure

```
week0/
  crmls_listed.py        # extraction → monthly listings CSV
  crmls_sold.py          # extraction → monthly sold CSV
week1/
  concatenate_monthly.py # combine all months → listings.csv + sold.csv (Residential only)
week2-3/
  common.py              # shared file-discovery + column keep-list (single source of truth)
  dataset_structuring.py # structure/validate sold, document types, filter, EDA, column-drop → reduced CSV
  mortgage_enrichment.py # merge FRED 30yr mortgage rate onto sold + listings → enriched CSVs
```

Data CSVs, Excel files, and Tableau `.twbx` workbooks are gitignored — this repo holds code and documentation only.

## The two-pipeline model

Two separate scripts, because listings and sold are two fundamentally different slices of the data:

- **Listings** — the full universe of properties placed on the market, regardless of outcome.
- **Sold** — the narrower subset that actually closed.

By the end of the summer there are only **two CSVs total** — `listings.csv` and `sold.csv`. Each week's run *updates the same two files* rather than creating a fresh pair.

## Weekly workflow (end to end)

1. Run the two Python scripts → update the same two CSVs (`listings.csv`, `sold.csv`).
2. Near the end of the internship, load both CSVs into **Tableau Public Desktop**.
3. Save the full working workbook as a `.twbx` (all worksheets visible).
4. Save a second `.twbx` with worksheets hidden and only dashboards visible.
5. Publish that version to **public.tableau.com**.

## How to run

Requires Python 3 with `requests` and `pandas`.

```bash
pip install requests pandas

# The Trestle proxy key is NOT stored in this repo — set it in your shell:
export TRESTLE_PROXY_KEY="<your IDX Exchange proxy key>"

# Week 0 — pull monthly files (defaults to 202602–202605; pass any YYYYMM args):
python3 week0/crmls_listed.py 202602 202603 202604 202605
python3 week0/crmls_sold.py   202602 202603 202604 202605

# Week 1 — combine all monthly files and filter to Residential.
# Point CRMLS_DATA_DIR at the folder of monthly CRMLS*.csv files:
export CRMLS_DATA_DIR="/path/to/monthly/files"
python3 week1/concatenate_monthly.py
```

---

## Weekly progress

### Week 0 — Extraction scripts

**Original brief:** the two extraction scripts were hardcoded to February 2026 and crashed with an `SSLEOFError` whenever the API dropped the connection. Both were rewritten so they:

- Accept one or more **`YYYYMM`** arguments from the command line (no more hardcoded month); output filenames derive from the month.
- Wrap every request in **retry + exponential backoff**, surviving dropped connections (the `SSLEOFError` / `SSLError` case, plus HTTP 429/5xx and mid-pull token expiry) instead of crashing.
- Read the API key from an **environment variable** rather than hardcoding it.

The scripts were then run to pull the Sold and Listing files for 202602–202605. Combined with the historical files retrieved via FileZilla, the team dataset now spans **January 2024 → May 2026**.

### Week 1 — Consolidation + Residential filter

**Deliverable:** `week1/concatenate_monthly.py` concatenates every monthly file (January 2024 through the most recently completed calendar month) into one **listings** and one **sold** dataset, filters both to `PropertyType == 'Residential'`, and writes the two CSVs — printing row counts at four checkpoints (before/after concatenation, before/after the filter) and recording them in the script's RUN LOG.

Observed on the 29-month set (Jan 2024 – May 2026):

| Dataset  | Monthly files | After concatenation | Residential (kept) |
|----------|--------------:|--------------------:|-------------------:|
| Listings | 29            | 729,251             | **480,383** (~66%) |
| Sold     | 29            | 655,362             | **438,115** (~67%) |

**Interpretation & insights**

- **Two source encodings.** The historical FileZilla files are **Windows-1252**, while the API-extraction files are **UTF-8**. A naive read crashes on byte `0x92` (a smart quote). The script reads each file as UTF-8 with a **cp1252 fallback** and writes clean UTF-8 — a real data-quality gotcha the team should standardize on going forward.
- **Concatenation is lossless** — the sum of the individual files equals the concatenated count for both datasets, confirming no rows are dropped on load.
- **`PropertyType` categorization.** Keeping only `Residential` removes roughly a third of all rows. The categories filtered out are `ResidentialLease`, `Land`, `ResidentialIncome`, `ManufacturedInPark`, `CommercialSale`, `CommercialLease`, and `BusinessOpportunity`. `Residential` still spans every residential subtype (single-family, condo, townhouse, etc.).
- **Stable residential share** across both slices (~66–67%), a sensible baseline for the market-level dashboards to come.

### Weeks 2–3 — Dataset structuring/validation + mortgage-rate enrichment

Two scripts plus a shared `common.py` (single source of truth for file discovery and the column keep-list). The first inspects, validates, and reduces the **sold** dataset; the second enriches **both** datasets with mortgage rates. Data now spans **Jan 2024 – June 2026 (30 months)** — the June 2026 files are picked up via a `YYYYMM` dedup across two data folders so newly-arrived months integrate without double-counting stale duplicates.

**`week2-3/dataset_structuring.py`** reads the 30 monthly Sold files **un-filtered** (so the property-type mix can be documented and the Residential filter genuinely demonstrated), then: reports structure (680,885 rows × 79 cols), documents all 8 property types, applies `PropertyType == 'Residential'`, builds null tables **before and after** the filter (flagging >90%-null columns), produces a numeric distribution summary for `ClosePrice`/`LivingArea`/`DaysOnMarket`, answers six EDA questions, applies the **column-drop decision**, and saves the reduced dataset.

| Property type (sold) | Rows | Share |
|---|--:|--:|
| Residential | 455,658 | 66.92% |
| ResidentialLease | 157,408 | 23.12% |
| Land | 22,173 | 3.26% |
| ManufacturedInPark | 18,564 | 2.73% |
| ResidentialIncome | 18,521 | 2.72% |
| CommercialSale / CommercialLease / BusinessOpportunity | 8,561 | 1.25% |

Residential filter kept **455,658** rows — an exact match to a teammate's independent 30-month result, asserted in-script as a continuity check (baseline lineage: 438,115 @ 29 mo → 455,658 @ 30 mo).

**Column-drop decision (79 → 31 columns).** Per the handbook clarification — drop columns >90% null, and keep only fields that feed the **Market Analysis** and **Competitive Analysis** dashboards — a 4-specialist review pruned the sold table to 31 columns: dropped **15** >90%-null columns plus **33** redundant/non-dashboard fields (kept one canonical each for id `ListingKey`, lot size `LotSizeSquareFeet`, list-agent `ListAgentFullName`; dropped amenities, schools, HOA, tax, address, co-agent, and originating-system fields). Kept: the price triad, date/DOM fields, status, property type/subtype, size/beds/baths/year, geography (county/city/zip/state/MLS-area/lat-long), and list/buyer office + agent fields.

**`week2-3/mortgage_enrichment.py`** fetches the FRED `MORTGAGE30US` 30-year fixed series (weekly, no API key), resamples it to monthly averages (664 months, 1971→2026), rebuilds the reduced Residential sold + listings via `common`, and left-merges the rate on a `year_month` key (sold←`CloseDate`, listings←`ListingContractDate`). Validation confirmed **0 null rates** on both (455,658 sold, 504,466 listings).

**Insights**
- **`>90%`-null flags shift with the population** (14 columns before the filter, 15 after — `BuildingAreaTotal` only crosses the line once non-Residential rows are removed), so the report keeps a null table for each stage.
- **EDA surfaced real dirt for the Weeks 4–5 cleaning phase** (flagged, not fixed): `DaysOnMarket` as low as **−288**, `LivingArea` of **0** and up to **17M** sqft, and 81 sold records with `CloseDate` before `ListingContractDate`.
- **Market read (Residential sold):** median close price **$815K**; days-on-market median **19**; **39.5%** closed above list vs **42.8%** below; Bay-Area counties lead on median price (Del Norte tops the list but on a tiny sample — an outlier to treat with care).
- **The mortgage merge is a clean monthly join** — every transaction month is covered by FRED, so no rows fall through.
- **Adding June was a clean, verifiable increment** — the new totals reproduce a teammate's independent numbers to the row, confirming both pipelines agree.
