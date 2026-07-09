"""
Weeks 2-3 Deliverable (Part 1 of 2) - Dataset Structuring & Validation (SOLD).

Inspects, documents, filters, and reduces the sold dataset. This script:

  1. Concatenates the 30 monthly Sold files (Jan 2024 - June 2026), UN-filtered, so the
     full property-type mix can be documented and the Residential filter genuinely
     demonstrated. File discovery dedups by YYYYMM across two data folders (see
     common.discover_monthly) so newly-arrived months are picked up without
     double-counting the stale duplicates in top-level data/.
  2. Reports structure (row/column counts, dtypes).
  3. Documents the unique property types found + counts (Residential vs. other).
  4. Applies the filter PropertyType == 'Residential'; asserts the result matches the
     current expected baseline (455,658 rows at 30 months) as a continuity check.
  5. Builds null-count tables (count + %) BEFORE and AFTER the filter; flags >90% null.
  6. Numeric distribution summary (min/max/mean/median/percentiles) for ClosePrice,
     LivingArea, DaysOnMarket on the filtered Residential base.
  7. Answers the six suggested intern EDA questions (market metrics on Residential only).
  8. COLUMN-DROP DECISION: drops every column not in the dashboard keep-list
     (common.KEEP_COLUMNS) -- this removes the >90%-null columns, redundant duplicates,
     and fields that don't feed the Market/Competitive Analysis dashboards -- and reports
     each dropped column grouped by reason. Saves the reduced Residential dataset.

Baseline lineage (continuity anchor): 438,115 Residential @ 29 months (thru May 2026)
                                   -> 455,658 Residential @ 30 months (thru June 2026).
"""

import os

import pandas as pd

import common

# --- Configuration -----------------------------------------------------------
OUTPUT_DIR = os.path.expanduser(os.environ.get("CRMLS_OUTPUT_DIR", "."))
SOLD_OUT = os.path.join(OUTPUT_DIR, "sold_residential_validated.csv")

# Continuity anchors for the current target state (30 months, Jan 2024 - June 2026).
EXPECTED_SOLD_PREFILTER = 680_885
EXPECTED_RESIDENTIAL_ROWS = 455_658

NUMERIC_FIELDS = ["ClosePrice", "LivingArea", "DaysOnMarket"]
PERCENTILES = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]


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
    return set(flagged)


def to_num(series):
    return pd.to_numeric(series, errors="coerce")


def numeric_distribution(df):
    print("\n=== NUMERIC DISTRIBUTION SUMMARY (Residential base) ===")
    rows = {}
    for col in NUMERIC_FIELDS:
        s = to_num(df[col]).dropna()
        stats = {"n": int(s.size), "min": s.min(), "max": s.max(),
                 "mean": round(s.mean(), 2), "median": s.median()}
        for p in PERCENTILES:
            stats[f"p{int(p*100)}"] = s.quantile(p)
        rows[col] = stats
    print(pd.DataFrame(rows).T.to_string())


def intern_questions(full, res):
    """Answer the six suggested intern EDA questions."""
    print("\n=== SUGGESTED INTERN QUESTIONS ===")
    share = (full["PropertyType"].value_counts(normalize=True) * 100).round(2)
    print("\nQ1  Property-type share (% of all sold rows):")
    print(share.to_string())

    cp = to_num(res["ClosePrice"]).dropna()
    print(f"\nQ2  ClosePrice  median=${cp.median():,.0f}  mean=${cp.mean():,.0f}")

    dom = to_num(res["DaysOnMarket"]).dropna()
    print("\nQ3  DaysOnMarket distribution:")
    print(f"    median={dom.median():.0f}  mean={dom.mean():.1f}  "
          f"p25={dom.quantile(.25):.0f}  p75={dom.quantile(.75):.0f}  max={dom.max():.0f}")

    lp = to_num(res["ListPrice"]); cp_full = to_num(res["ClosePrice"])
    both = pd.DataFrame({"cp": cp_full, "lp": lp}).dropna()
    both = both[both["lp"] > 0]
    above = (both["cp"] > both["lp"]).mean() * 100
    below = (both["cp"] < both["lp"]).mean() * 100
    equal = (both["cp"] == both["lp"]).mean() * 100
    print(f"\nQ4  vs list price (n={len(both):,}):  above={above:.1f}%  "
          f"below={below:.1f}%  at_list={equal:.1f}%")

    ld = pd.to_datetime(res["ListingContractDate"], errors="coerce")
    cd = pd.to_datetime(res["CloseDate"], errors="coerce")
    dd = pd.DataFrame({"ld": ld, "cd": cd}).dropna()
    close_before_list = (dd["cd"] < dd["ld"]).sum()
    print(f"\nQ5  Date consistency (n={len(dd):,}):  "
          f"CloseDate < ListingContractDate = {close_before_list:,} "
          f"({close_before_list/len(dd)*100:.2f}%)")

    tmp = res.copy(); tmp["_cp"] = cp_full
    med = (tmp.dropna(subset=["_cp"]).groupby("CountyOrParish")["_cp"]
              .median().sort_values(ascending=False))
    print("\nQ6  Top 10 counties by median ClosePrice:")
    print(med.head(10).round(0).to_string())


def report_column_drop(df, over90):
    """Document the column-drop: which columns go, grouped by reason."""
    print("\n=== COLUMN-DROP DECISION (dashboard keep-list) ===")
    keep = [c for c in common.KEEP_COLUMNS if c in df.columns]
    drop = [c for c in df.columns if c not in common.KEEP_COLUMNS]
    drop_over90 = [c for c in drop if c in over90]
    drop_other = [c for c in drop if c not in over90]
    print(f"keeping {len(keep)} of {df.shape[1]} columns for the Market + "
          f"Competitive Analysis dashboards.")
    print(f"\ndropped -- >90% null ({len(drop_over90)}): {drop_over90}")
    print(f"\ndropped -- redundant / not dashboard-relevant ({len(drop_other)}): {drop_other}")
    print(f"\nKEPT ({len(keep)}): {keep}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=== STRUCTURE (un-filtered SOLD pool) ===")
    sold, n_files, rows_sum = common.load_unfiltered("Sold")
    print(f"monthly Sold files: {n_files} | rows summed: {rows_sum:,} | "
          f"after concat: {len(sold):,} (lossless)")
    assert len(sold) == EXPECTED_SOLD_PREFILTER, (
        f"pre-filter rows {len(sold):,} != expected {EXPECTED_SOLD_PREFILTER:,}")
    print(f"\nshape: {sold.shape[0]:,} rows x {sold.shape[1]} columns")
    print("\ncolumn dtypes:")
    print(sold.dtypes.to_string())

    print("\n=== UNIQUE PROPERTY TYPES FOUND ===")
    print(sorted(sold["PropertyType"].dropna().unique().tolist()))
    print("\ncounts:")
    print(sold["PropertyType"].value_counts(dropna=False).to_string())

    null_report(sold, "before Residential filter")

    print("\n=== FILTER: PropertyType == 'Residential' ===")
    residential = sold[sold["PropertyType"] == "Residential"].copy()
    print(f"rows kept: {len(residential):,} of {len(sold):,} "
          f"({len(residential)/len(sold)*100:.1f}%)")
    assert sorted(residential["PropertyType"].unique().tolist()) == ["Residential"]
    assert len(residential) == EXPECTED_RESIDENTIAL_ROWS, (
        f"Residential rows {len(residential):,} != baseline {EXPECTED_RESIDENTIAL_ROWS:,}")
    print(f"continuity check OK: matches 30-month baseline ({EXPECTED_RESIDENTIAL_ROWS:,}).")

    over90 = null_report(residential, "after Residential filter")
    numeric_distribution(residential)
    intern_questions(sold, residential)

    # Column-drop decision + reduced save.
    report_column_drop(residential, over90)
    reduced = common.apply_keep(residential)
    assert "CloseDate" in reduced.columns, "join key CloseDate dropped!"
    reduced.to_csv(SOLD_OUT, index=False)
    print(f"\nsaved reduced Residential sold -> {SOLD_OUT}  "
          f"({len(reduced):,} rows x {reduced.shape[1]} cols)")


if __name__ == "__main__":
    main()


# =============================================================================
# RUN LOG (observed) - 30 monthly Sold files (Jan 2024 - June 2026)
# -----------------------------------------------------------------------------
# STRUCTURE: 30 files | rows summed 680,885 | after concat 680,885 (lossless)
#            shape 680,885 rows x 79 columns
# TYPES (counts): Residential 455,658 | ResidentialLease 157,408 | Land 22,173 |
#            ManufacturedInPark 18,564 | ResidentialIncome 18,521 |
#            CommercialSale 4,451 | CommercialLease 3,621 | BusinessOpportunity 489
# FILTER Residential: 455,658 of 680,885 (66.9%) -- continuity check PASSED
#            (baseline 438,115 @ 29mo -> 455,658 @ 30mo; matches teammate's count)
# NUMERIC DISTRIBUTION (Residential):
#   ClosePrice   n=455,656  min=525    median=815,000  mean=1,124,047  max=110,000,000
#   LivingArea   n=455,388  min=0      median=1,643    mean=1,900      max=17,021,321
#   DaysOnMarket n=455,658  min=-288   median=19       mean=37.6       max=12,430
#   (min<=0 / negative are outliers flagged for the Weeks 4-5 cleaning phase.)
# INTERN QUESTIONS:
#   Q1 share: Residential 66.92% | ResidentialLease 23.12% | rest <3.3%
#   Q2 median $815,000 | mean $1,124,047
#   Q3 DaysOnMarket median 19 | mean 37.6 | p25 8 | p75 49
#   Q4 vs list: above 39.5% | below 42.8% | at list 17.7%
#   Q5 CloseDate < ListingContractDate: 81 rows (0.02%)
#   Q6 top counties by median: Del Norte 6.74M (tiny-n outlier), San Mateo 1.65M,
#      Santa Clara 1.54M, Orange 1.18M, Santa Cruz 1.18M
# COLUMN-DROP: kept 31 of 79 (dashboard keep-list); dropped 15 >90%-null + 33
#      redundant/not-dashboard-relevant. saved 455,658 rows x 31 cols.
# =============================================================================
