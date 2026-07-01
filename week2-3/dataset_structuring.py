"""
Weeks 2-3 Deliverable (Part 1 of 2) - Dataset Structuring & Validation (SOLD).

Before any analytics, the sold dataset is inspected, its property-type composition
documented, filtered to Residential, and validated. This script:

  1. Concatenates the 29 monthly Sold files (Jan 2024 - May 2026), UN-filtered, so the
     full property-type mix can be documented and the Residential filter genuinely
     demonstrated. (Reusing Week 1's utf-8 -> cp1252 encoding-safe reader; concat is
     asserted lossless.)
  2. Reports structure: row/column counts and column dtypes.
  3. Documents the unique property types found + their counts (Residential vs. other).
  4. Applies the filtering logic: PropertyType == 'Residential'. As a continuity check
     against the Week 1 deliverable, asserts the result is exactly 438,115 rows and that
     PropertyType.unique() == ['Residential'].
  5. Builds null-count summary tables (count + %) BEFORE and AFTER the filter, and flags
     any column > 90% null.
  6. Produces a numeric distribution summary (min, max, mean, median, percentiles) for
     ClosePrice, LivingArea, and DaysOnMarket on the filtered Residential base.
  7. Answers the six suggested intern EDA questions (all market metrics on the filtered
     Residential base only -- leases/land/commercial would poison the aggregates).
  8. Saves the filtered Residential dataset as a new CSV.

WHY read the un-filtered monthly files instead of the Week 1 output? The Week 1 CSV is
already 100% Residential, so PropertyType.unique() would be ['Residential'] and the
"document property types / filtering logic" requirement would be a no-op. A council of
four analytics specialists (data engineering, data quality, statistical EDA, real-estate
domain) ruled 4-0 to read the un-filtered local files. Re-concatenating LOCAL files is
not an API re-pull -- no new data is fetched.

Observed run counts are recorded in the RUN LOG at the bottom.
"""

import glob
import os

import pandas as pd

# --- Configuration -----------------------------------------------------------
# Folder holding the 29 per-month Sold files, named CRMLSSold<YYYYMM>.csv. Override
# with env vars so this runs on any machine. Data files are gitignored / local only.
DATA_DIR = os.path.expanduser(
    os.environ.get("CRMLS_DATA_DIR",
                   "~/idx-exchange/data/Listing & Sold (Jan 2024 - May 2026)")
)
OUTPUT_DIR = os.path.expanduser(os.environ.get("CRMLS_OUTPUT_DIR", "."))
SOLD_OUT = os.path.join(OUTPUT_DIR, "sold_residential_validated.csv")

# Continuity check against the Week 1 deliverable (Residential sold row count).
EXPECTED_RESIDENTIAL_ROWS = 438_115

# Fields required by the deliverable's numeric distribution summary.
NUMERIC_FIELDS = ["ClosePrice", "LivingArea", "DaysOnMarket"]
PERCENTILES = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]


def read_any(path):
    """Read a CSV as UTF-8, falling back to Windows-1252 for the FileZilla files."""
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="cp1252")


def load_unfiltered_sold():
    """Concatenate every monthly Sold file (un-filtered). Asserts a lossless concat."""
    pattern = os.path.join(DATA_DIR, "CRMLSSold[0-9][0-9][0-9][0-9][0-9][0-9].csv")
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No monthly Sold files found under: {DATA_DIR}")

    print(f"monthly Sold files found: {len(files)} "
          f"({os.path.basename(files[0])} ... {os.path.basename(files[-1])})")

    frames, rows_sum = [], 0
    for f in files:
        df = read_any(f)
        rows_sum += len(df)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    print(f"rows summed across monthly files: {rows_sum:,}")
    print(f"rows after concatenation:        {len(combined):,}")
    assert len(combined) == rows_sum, "Concatenation dropped/added rows -- not lossless!"
    return combined


def null_report(df, label):
    """Null-count summary table (count + %) with a > 90% null flag column."""
    counts = df.isnull().sum()
    pct = (counts / len(df) * 100).round(2)
    report = pd.DataFrame({"null_count": counts, "null_pct": pct})
    report["over_90pct_null"] = report["null_pct"] > 90
    report = report.sort_values("null_pct", ascending=False)
    flagged = report.index[report["over_90pct_null"]].tolist()
    print(f"\n--- NULL REPORT ({label}) ---")
    print(f"columns: {df.shape[1]} | rows: {len(df):,}")
    print(report.to_string())
    print(f"columns > 90% null ({len(flagged)}): {flagged}")
    return report, flagged


def to_num(series):
    """Coerce a column to numeric for distribution/market math (bad values -> NaN)."""
    return pd.to_numeric(series, errors="coerce")


def numeric_distribution(df):
    """min/max/mean/median + percentile summary for the required numeric fields."""
    print("\n=== NUMERIC DISTRIBUTION SUMMARY (Residential base) ===")
    rows = {}
    for col in NUMERIC_FIELDS:
        s = to_num(df[col]).dropna()
        stats = {
            "n": int(s.size), "min": s.min(), "max": s.max(),
            "mean": round(s.mean(), 2), "median": s.median(),
        }
        for p in PERCENTILES:
            stats[f"p{int(p*100)}"] = s.quantile(p)
        rows[col] = stats
    summary = pd.DataFrame(rows).T
    print(summary.to_string())
    return summary


def intern_questions(full, res):
    """Answer the six suggested intern EDA questions (locked into scope by the user).

    `full` = un-filtered pool (for the type-share question); `res` = Residential base
    (all market metrics computed here so leases/land/commercial don't poison aggregates).
    """
    print("\n=== SUGGESTED INTERN QUESTIONS ===")

    # Q1 - Residential vs. other property-type share (needs the un-filtered pool).
    share = (full["PropertyType"].value_counts(normalize=True) * 100).round(2)
    print("\nQ1  Property-type share (% of all sold rows):")
    print(share.to_string())

    # Q2 - Median and average close price (Residential).
    cp = to_num(res["ClosePrice"]).dropna()
    print(f"\nQ2  ClosePrice  median=${cp.median():,.0f}  mean=${cp.mean():,.0f}")

    # Q3 - Days on Market distribution (Residential).
    dom = to_num(res["DaysOnMarket"]).dropna()
    print("\nQ3  DaysOnMarket distribution:")
    print(f"    median={dom.median():.0f}  mean={dom.mean():.1f}  "
          f"p25={dom.quantile(.25):.0f}  p75={dom.quantile(.75):.0f}  max={dom.max():.0f}")

    # Q4 - % sold above vs. below list price (ClosePrice vs. ListPrice).
    lp = to_num(res["ListPrice"])
    cp_full = to_num(res["ClosePrice"])
    both = pd.DataFrame({"cp": cp_full, "lp": lp}).dropna()
    both = both[both["lp"] > 0]
    above = (both["cp"] > both["lp"]).mean() * 100
    below = (both["cp"] < both["lp"]).mean() * 100
    equal = (both["cp"] == both["lp"]).mean() * 100
    print(f"\nQ4  vs list price (n={len(both):,}):  above={above:.1f}%  "
          f"below={below:.1f}%  at_list={equal:.1f}%")

    # Q5 - Date consistency: CloseDate before ListingContractDate (negative timeline).
    ld = pd.to_datetime(res["ListingContractDate"], errors="coerce")
    cd = pd.to_datetime(res["CloseDate"], errors="coerce")
    dd = pd.DataFrame({"ld": ld, "cd": cd}).dropna()
    close_before_list = (dd["cd"] < dd["ld"]).sum()
    print(f"\nQ5  Date consistency (n={len(dd):,}):  "
          f"CloseDate < ListingContractDate = {close_before_list:,} "
          f"({close_before_list/len(dd)*100:.2f}%)")

    # Q6 - Counties with the highest median close price (Residential).
    tmp = res.copy()
    tmp["_cp"] = cp_full
    med = (tmp.dropna(subset=["_cp"])
              .groupby("CountyOrParish")["_cp"].median()
              .sort_values(ascending=False))
    print("\nQ6  Top 10 counties by median ClosePrice:")
    print(med.head(10).round(0).to_string())


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1-2. Load un-filtered pool + structure.
    print("=== STRUCTURE (un-filtered SOLD pool) ===")
    sold = load_unfiltered_sold()
    print(f"\nshape: {sold.shape[0]:,} rows x {sold.shape[1]} columns")
    print("\ncolumn dtypes:")
    print(sold.dtypes.to_string())

    # 3. Document property types.
    print("\n=== UNIQUE PROPERTY TYPES FOUND ===")
    print(sorted(sold["PropertyType"].dropna().unique().tolist()))
    print("\ncounts:")
    print(sold["PropertyType"].value_counts(dropna=False).to_string())

    # 5a. Null report BEFORE filter.
    null_report(sold, "before Residential filter")

    # 4. Filtering logic + continuity check.
    print("\n=== FILTER: PropertyType == 'Residential' ===")
    residential = sold[sold["PropertyType"] == "Residential"].copy()
    print(f"rows kept: {len(residential):,} of {len(sold):,} "
          f"({len(residential)/len(sold)*100:.1f}%)")
    assert sorted(residential["PropertyType"].unique().tolist()) == ["Residential"]
    assert len(residential) == EXPECTED_RESIDENTIAL_ROWS, (
        f"Residential row count {len(residential):,} != Week 1 baseline "
        f"{EXPECTED_RESIDENTIAL_ROWS:,} -- inputs diverged!")
    print(f"continuity check OK: matches Week 1 baseline ({EXPECTED_RESIDENTIAL_ROWS:,}).")

    # 5b. Null report AFTER filter.
    null_report(residential, "after Residential filter")

    # 6. Numeric distribution summary.
    numeric_distribution(residential)

    # 7. Suggested intern questions.
    intern_questions(sold, residential)

    # 8. Save filtered dataset.
    residential.to_csv(SOLD_OUT, index=False)
    print(f"\nsaved filtered Residential sold -> {SOLD_OUT}  ({len(residential):,} rows)")


if __name__ == "__main__":
    main()


# =============================================================================
# RUN LOG (observed) - run on the 29 monthly Sold files (Jan 2024 - May 2026)
# -----------------------------------------------------------------------------
# STRUCTURE
#   rows summed across monthly files: 655,362
#   rows after concatenation:         655,362   (lossless)
#   shape: 655,362 rows x 79 columns
#
# UNIQUE PROPERTY TYPES FOUND (counts):
#   Residential 438,115 | ResidentialLease 151,756 | Land 21,459 |
#   ManufacturedInPark 17,935 | ResidentialIncome 17,823 | CommercialSale 4,314 |
#   CommercialLease 3,489 | BusinessOpportunity 471
#
# FILTER: PropertyType == 'Residential'
#   rows kept: 438,115 of 655,362 (66.9%)  -- continuity check vs Week 1 PASSED
#
# COLUMNS > 90% NULL:  14 before filter, 15 after filter (BuildingAreaTotal crosses
#   the 90% line only after filtering to Residential -- hence two null tables).
#
# NUMERIC DISTRIBUTION (Residential base):
#   ClosePrice    n=438,113  min=525        median=815,000  mean=1,121,740  max=110,000,000
#   LivingArea    n=437,853  min=0          median=1,641    mean=1,900      max=17,021,321
#   DaysOnMarket  n=438,115  min=-288       median=19       mean=37.7       max=12,430
#   (min<=0 / negative values are outliers flagged here for the Weeks 4-5 cleaning phase.)
#
# INTERN QUESTIONS:
#   Q1 type share: Residential 66.85% | ResidentialLease 23.16% | Land 3.27% | rest <3%
#   Q2 ClosePrice median $815,000 | mean $1,121,740
#   Q3 DaysOnMarket median 19 | mean 37.7 | p25 8 | p75 49
#   Q4 vs list price: above 39.5% | below 42.8% | at list 17.7%
#   Q5 date consistency: CloseDate < ListingContractDate in 78 rows (0.02%)
#   Q6 top counties by median ClosePrice: Del Norte 6.74M (tiny-n outlier), San Mateo
#      1.65M, Santa Clara 1.54M, Santa Cruz 1.18M, Orange / San Francisco 1.18M
# =============================================================================
