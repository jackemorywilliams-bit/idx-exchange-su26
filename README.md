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
  make_figures.py        # README figures (column keep/drop, mortgage-rate line)
week4-5/
  data_cleaning.py       # type dates/numerics, flag quality issues, emit flagged + clean-view CSVs
  make_figures.py        # README figure (data-quality flag prevalence)
```

Data CSVs, Excel files, and Tableau `.twbx` workbooks are gitignored — this repo holds code and documentation only.

## The two-pipeline model

Two separate scripts, because listings and sold are two fundamentally different slices of the data:

- **Listings** — the full universe of properties placed on the market, regardless of outcome.
- **Sold** — the narrower subset that actually closed.

There are two canonical **raw** datasets — `listings.csv` and `sold.csv` — which each month's pull grows in place. Later stages derive enriched and cleaned versions *from* them (reduced → rate-enriched → flagged + clean-view; see Weeks 2–5), always as separate downstream artifacts, never by mutating the raw pair.

## Weekly workflow (end to end)

1. Run the two extraction scripts → update the two raw datasets.
2. Run the downstream stages (Weeks 2–5) to produce the enriched, cleaned versions.
3. Near the end of the internship, load the two Weeks 4–5 **clean-view** CSVs into **Tableau Public Desktop**.
4. Save the full working workbook as a `.twbx` (all worksheets visible).
5. Save a second `.twbx` with worksheets hidden and only dashboards visible.
6. Publish that version to **public.tableau.com**.

## How to run

Requires Python 3 with `requests` and `pandas` (plus `matplotlib` for the figure scripts).

```bash
pip install requests pandas matplotlib

# The Trestle proxy key is NOT stored in this repo — set it in your shell:
export TRESTLE_PROXY_KEY="<your IDX Exchange proxy key>"

# Week 0 — pull monthly files (defaults to 202602–202605; pass any YYYYMM args):
python3 week0/crmls_listed.py 202602 202603 202604 202605
python3 week0/crmls_sold.py   202602 202603 202604 202605

# Week 1 — combine all monthly files and filter to Residential.
# Point CRMLS_DATA_DIR at the folder of monthly CRMLS*.csv files:
export CRMLS_DATA_DIR="/path/to/monthly/files"
python3 week1/concatenate_monthly.py

# Weeks 2–3 — structure/reduce sold, then enrich both datasets with FRED rates:
export CRMLS_OUTPUT_DIR="/path/to/deliverables"
python3 week2-3/dataset_structuring.py
python3 week2-3/mortgage_enrichment.py

# Weeks 4–5 — type, flag, and emit flagged + clean-view CSVs
# (reads the Weeks 2–3 "With Rates" files from CRMLS_DELIV_DIR):
export CRMLS_DELIV_DIR="$CRMLS_OUTPUT_DIR"
python3 week4-5/data_cleaning.py
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

*(Totals as of the original 29-month set; June 2026 was added in Weeks 2–3 — see the lineage notes there.)*

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
| CommercialSale / CommercialLease / BusinessOpportunity | 8,561 | 1.26% |

<sub>Shares are rounded and may not sum to exactly 100%.</sub>

Residential filter kept **455,658** rows — an exact match to a teammate's independent 30-month result, asserted in-script as a continuity check (baseline lineage: 438,115 @ 29 mo → 455,658 @ 30 mo).

**Column-drop decision (79 → 31 columns).** Per the handbook clarification — drop columns >90% null, and keep only fields that feed the **Market Analysis** and **Competitive Analysis** dashboards — a 4-specialist review pruned the sold table to 31 columns: dropped **15** >90%-null columns plus **33** redundant/non-dashboard fields (kept one canonical each for id `ListingKey`, lot size `LotSizeSquareFeet`, list-agent `ListAgentFullName`; dropped amenities, schools, HOA, tax, address, co-agent, and originating-system fields).

![Column keep/drop breakdown: 79 to 31 columns](week2-3/figures/columns_kept_dropped.png)

**The 31 columns kept** (by dashboard purpose):

| Purpose | Columns |
|---|---|
| id / join key | `ListingKey` |
| price | `ClosePrice`, `ListPrice`, `OriginalListPrice` |
| dates + time-on-market | `CloseDate`, `ListingContractDate`, `PurchaseContractDate`, `DaysOnMarket` |
| status + product mix | `MlsStatus`, `PropertyType`, `PropertySubType` |
| size / attributes | `LivingArea`, `LotSizeSquareFeet`, `BedroomsTotal`, `BathroomsTotalInteger`, `YearBuilt` |
| geography | `CountyOrParish`, `City`, `PostalCode`, `StateOrProvince`, `MLSAreaMajor`, `Latitude`, `Longitude` |
| competitive — offices | `ListOfficeName`, `BuyerOfficeName` |
| competitive — agents | `ListAgentFullName`, `ListAgentAOR`, `BuyerAgentFirstName`, `BuyerAgentLastName`, `BuyerAgentMlsId`, `BuyerAgentAOR` |

**The 48 columns dropped** (by reason):

| Reason | Columns |
|---|---|
| >90% null (15) | `WaterfrontYN`, `BasementYN`, `FireplacesTotal`, `AboveGradeFinishedArea`, `TaxAnnualAmount`, `BuilderName`, `TaxYear`, `BuildingAreaTotal`, `ElementarySchoolDistrict`, `CoBuyerAgentFirstName`, `BelowGradeFinishedArea`, `BusinessType`, `CoveredSpaces`, `LotSizeDimensions`, `MiddleOrJuniorSchoolDistrict` |
| redundant duplicate (10) | `ListingKeyNumeric`, `ListingId` (→`ListingKey`); `LotSizeAcres`, `LotSizeArea` (→`LotSizeSquareFeet`); `ListAgentFirstName`, `ListAgentLastName` (→`ListAgentFullName`); `UnparsedAddress`, `StreetNumberNumeric`; `OriginatingSystemName`, `OriginatingSystemSubName` |
| not dashboard-relevant (23) | `Flooring`, `ViewYN`, `PoolPrivateYN`, `CoListOfficeName`, `CoListAgentFirstName`, `CoListAgentLastName`, `AssociationFeeFrequency`, `ElementarySchool`, `AttachedGarageYN`, `ParkingTotal`, `SubdivisionName`, `BuyerOfficeAOR`, `ContractStatusChangeDate`, `MiddleOrJuniorSchool`, `FireplaceYN`, `Stories`, `HighSchool`, `Levels`, `MainLevelBedrooms`, `NewConstructionYN`, `GarageSpaces`, `HighSchoolDistrict`, `AssociationFee` |

**`week2-3/mortgage_enrichment.py`** fetches the FRED `MORTGAGE30US` 30-year fixed series (weekly, no API key), resamples it to monthly averages (664 months, 1971→2026), rebuilds the reduced Residential sold + listings via `common`, and left-merges the rate on a `year_month` key (sold←`CloseDate`, listings←`ListingContractDate`). Validation confirmed **0 null rates** on both (455,658 sold, 504,466 listings; listings lineage: 480,383 @ 29 mo → 504,466 @ 30 mo).

Only the **30 months that overlap the MLS data (Jan 2024 – Jun 2026)** are joined onto transactions. Over that window the 30-yr fixed rate ranged **6.05% (Feb 2026, low) → 7.06% (May 2024, high)**, ending at **6.49%** (Jun 2026):

![US 30-year fixed mortgage rate, monthly average, Jan 2024 to Jun 2026 (FRED MORTGAGE30US)](week2-3/figures/mortgage_rate_30yr.png)

<sub>Source: FRED `MORTGAGE30US` (weekly, Freddie Mac) resampled to a monthly average.</sub>

| Month | Rate | Month | Rate | Month | Rate |
|---|--:|---|--:|---|--:|
| 2024-01 | 6.64% | 2024-11 | 6.80% | 2025-09 | 6.35% |
| 2024-02 | 6.78% | 2024-12 | 6.71% | 2025-10 | 6.25% |
| 2024-03 | 6.82% | 2025-01 | 6.96% | 2025-11 | 6.24% |
| 2024-04 | 6.99% | 2025-02 | 6.84% | 2025-12 | 6.19% |
| 2024-05 | **7.06%** | 2025-03 | 6.65% | 2026-01 | 6.10% |
| 2024-06 | 6.92% | 2025-04 | 6.72% | 2026-02 | **6.05%** |
| 2024-07 | 6.85% | 2025-05 | 6.82% | 2026-03 | 6.18% |
| 2024-08 | 6.50% | 2025-06 | 6.82% | 2026-04 | 6.33% |
| 2024-09 | 6.18% | 2025-07 | 6.72% | 2026-05 | 6.44% |
| 2024-10 | 6.43% | 2025-08 | 6.59% | 2026-06 | 6.49% |

**Insights**
- **`>90%`-null flags shift with the population** (14 columns before the filter, 15 after — `BuildingAreaTotal` only crosses the line once non-Residential rows are removed), so the report keeps a null table for each stage.
- **EDA surfaced real dirt for the Weeks 4–5 cleaning phase** (flagged, not fixed): `DaysOnMarket` as low as **−288**, `LivingArea` of **0** and up to **17M** sqft, and 81 sold records with `CloseDate` before `ListingContractDate`.
- **Market read (Residential sold):** median close price **$815K**; days-on-market median **19**; **39.5%** closed above list vs **42.8%** below; Bay-Area counties lead on median price (Del Norte tops the list but on a tiny sample — an outlier to treat with care).
- **The mortgage merge is a clean monthly join** — every transaction month is covered by FRED, so no rows fall through.
- **Adding June was a clean, verifiable increment** — the new totals reproduce a teammate's independent numbers to the row, confirming both pipelines agree.

### Weeks 4–5 — Data cleaning & preparation

**What this week does, in one sentence:** find every bad or suspicious value in the data, mark it, and remove only the rows that are truly impossible — so the analysis that follows can be trusted.

**`week4-5/data_cleaning.py`** works in three steps:

1. **Fix the column types.** Dates were stored as plain text; the script converts them into real dates so they can be sorted and compared. Numeric fields are confirmed to be real numbers.
2. **Mark problems instead of deleting them.** Every quality issue gets its own true/false **flag** column, so nothing is silently thrown away — a flagged row can always be inspected or filtered later.
3. **Save two files per dataset:**
   - a **flagged** file — every row kept, all flags attached (the audit trail), and
   - a **clean view** — the same data with only the *impossible* rows removed (a $0 sale, a 0-sqft home, negative days on market). Everything else stays in, flagged.

The flags fall into four groups:

| Group | What it catches | Example |
|---|---|---|
| Impossible numbers | Values that cannot be real. These are the **only** rows removed from the clean view. | price ≤ $0, size ≤ 0 sqft, negative days on market, negative beds/baths |
| Dates out of order | A sale can't close before it was listed. | close date earlier than listing date |
| Bad map coordinates | Missing, zeroed, or outside California. | longitude with the wrong sign |
| Worth a second look | Real-looking but extreme values, kept but flagged. | price under $10k or over $100M, home over 25,000 sqft |

Three details worth knowing: a row with a *missing* date is never flagged (it can't be checked, so it's "unaudited," not "clean"); the review thresholds are deliberately round numbers ($10k, $100M, 25k sqft) so anyone can understand and challenge them; and flags are saved as **0/1 integers** rather than True/False — easier to use in Tableau and consistent with the team's other files. The "dates out of order" flag counts *any* out-of-order pair (405 rows); the stricter "entire timeline reversed" reading catches just 1 row — both counts are printed so results stay comparable across the team.

> **"Clean" here means one specific thing:** free of impossible numbers. Rows with date or map issues are still in the clean view, carrying their flags — filter on a flag column if you want a stricter cut.

![Data-quality flags on the sold dataset — missing coordinates dominate; every other issue is under 0.1%](week4-5/figures/data_quality_flags.png)

**What the flags found (sold dataset, 455,658 rows):**

| Issue | Rows | % of data |
|---|--:|--:|
| No map coordinates (`missing_coords_flag`) | 53,637 | 11.77% |
| Dates out of order (any kind) | 405 | 0.089% |
| Size recorded as 0 or negative | 161 | 0.035% |
| Purchase date after closing date | 92 | 0.020% |
| Listing date after closing date | 81 | 0.018% |
| Coordinates outside California | 65 | 0.014% |
| Negative days on market | 48 | 0.011% |
| Coordinates recorded as exactly 0 | 44 | 0.010% |
| Longitude has the wrong sign | 34 | 0.007% |
| Size over 25,000 sqft | 15 | 0.003% |
| Price under $10k | 9 | 0.002% |
| Year built implausible | 9 | 0.002% |
| Price over $100M | 2 | <0.001% |
| **Flagged for review (any flag)** | **54,126** | **11.88%** |
| **Impossible → removed from clean view** | **209** | **0.046%** |

Bottom line: only **209** sold rows (0.046%) were bad enough to remove, leaving a **455,449-row clean view**. Listings came out the same way: 304 removed from 504,466, leaving 504,162. (Some geographic counts overlap on purpose — a wrong-sign longitude is, by definition, also outside California.)

**What we learned**

- **The one real problem: missing map coordinates — and they're not missing at random.** About 12% of homes have no location point. Almost all of them are **2024 sales** (28% of that year is missing, vs. under 1% afterward), they cluster in **Bay-Area counties** (Santa Clara is 35% missing), and they skew **~$100K more expensive** than homes that do have coordinates. Plain consequence: a map built from this data quietly leaves out 2024, Northern California, and pricier homes. The fix: for anything grouped by geography, use the county/city/zip columns instead — those are 100% filled in.
- **Don't stack the two datasets.** About 94% of sold homes *also* appear in the listings file (a sold home was once listed — obvious in hindsight). Combining the files naively would count ~428K sales twice.
- **"Days on market" is not what you'd calculate yourself.** The MLS computes it from its own status events. It matches "close date minus list date" only about half the time. If you need your own duration math, do it on rows without the timeline flag.
- **The scary errors turned out to be tiny.** The −288 days-on-market, the 17-million-sqft "home," the sales that closed before listing — all real, all flagged, and all together just a few hundred rows out of 455K. One honest note: the removed 0-sqft homes are mostly *expensive* real sales (median ~$1.8M) where the size was simply never entered — so removing them trims a sliver off the luxury end.
- **Why flag instead of delete?** Because zero is sometimes legitimate: a home *can* sell in 0 days, land *can* have 0 bedrooms. Deleting on simple rules would throw away real data. So the script deletes only the impossible and marks everything else.
- One handbook field (`ContractStatusChangeDate`) isn't converted because we deliberately dropped it in Weeks 2–3 (it doesn't feed any dashboard). The code will pick it up automatically if it ever comes back.
