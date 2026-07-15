"""
Weeks 4-5 Deliverable - Data Cleaning & Preparation.

Takes the Weeks 2-3 mortgage-enriched, Residential, dashboard-reduced datasets and
prepares them for reliable analytics. This script (non-destructively) TYPES the data,
FLAGS every quality issue as a boolean column, and emits two artifacts per dataset:
a fully-flagged file (all rows kept, for audit) and a "clean view" (only the
unambiguous numeric-error rows removed, for analysis).

Steps:
  1. Type conversion:
       - dates -> datetime (CloseDate, ListingContractDate, PurchaseContractDate),
         normalized to midnight; unparseable -> NaT.
       - numeric fields -> numeric; unparseable -> NaN.
     (ContractStatusChangeDate is named by the handbook but was intentionally dropped
      in the Weeks 2-3 column-reduction as non-dashboard; only dates actually present
      are converted. The loop is guarded so it is picked up automatically if ever
      re-added to the keep-list.)

  2. Invalid-numeric flags (the removal criteria; handbook: "remove or flag"):
       invalid_closeprice_flag  ClosePrice <= 0        (NaN prices never flag)
       invalid_livingarea_flag  LivingArea <= 0
       negative_dom_flag        DaysOnMarket < 0        (0 is valid: same-day sale)
       negative_beds_flag       BedroomsTotal < 0       (0 is valid: land/studio)
       negative_baths_flag      BathroomsTotalInteger < 0
       -> hard_invalid_flag = OR of the five. The clean view drops these rows.

  3. Date-consistency flags (review only; strict '>' so same-day is OK; NaT-safe):
       listing_after_close_flag   ListingContractDate > CloseDate
       purchase_after_close_flag  PurchaseContractDate > CloseDate
       negative_timeline_flag     any break in Listing <= Purchase <= Close

  4. Geographic flags (review only; California coords are negative-longitude):
       missing_coords_flag     Latitude or Longitude null
       zero_coord_flag         Latitude == 0 or Longitude == 0 (sentinel null)
       positive_longitude_flag Longitude > 0 (sign error)
       out_of_ca_flag          real coordinate outside the CA bounding box

  5. Review-outlier flags (non-destructive; tied to dirt seen in Weeks 2-3 EDA):
       suspicious_low_price_flag  0 < ClosePrice < 10,000  (non-arms-length / nominal)
       extreme_high_price_flag    ClosePrice > 100,000,000
       extreme_livingarea_flag    LivingArea > 25,000 sqft
       implausible_yearbuilt_flag YearBuilt < 1850 or > next year

  6. Validation summary: per-flag count + %, the any_review_flag total, hard-invalid
     total, and the clean-view row count. Rows are only ever removed by hard_invalid.
"""

import os

import pandas as pd

# --- Configuration -----------------------------------------------------------
DELIV = os.path.expanduser(os.environ.get(
    "CRMLS_DELIV_DIR", "~/idx-exchange/deliverables"))
OUTPUT_DIR = os.path.expanduser(os.environ.get("CRMLS_OUTPUT_DIR", DELIV))

INPUTS = {
    "Sold": os.path.join(DELIV, "Week 2-3 _ Deliverable _ Sold With Rates.csv"),
    "Listing": os.path.join(DELIV, "Week 2-3 _ Deliverable _ Listings With Rates.csv"),
}
EXPECTED_ROWS = {"Sold": 455_658, "Listing": 504_466}

# California bounding box (review, not a hard cutoff -- legit border parcels exist).
LAT_MIN, LAT_MAX = 32.5, 42.05
LON_MIN, LON_MAX = -124.5, -114.1

DATE_COLS = ["ListingContractDate", "PurchaseContractDate", "CloseDate"]
NUMERIC_COLS = ["ClosePrice", "ListPrice", "OriginalListPrice", "LivingArea",
                "LotSizeSquareFeet", "DaysOnMarket", "BedroomsTotal",
                "BathroomsTotalInteger", "YearBuilt", "Latitude", "Longitude",
                "rate_30yr_fixed"]
NEXT_YEAR = 2027  # current year (2026) + 1


def read_any(path):
    """Read a CSV as UTF-8, falling back to Windows-1252 (self-contained reader)."""
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="cp1252")


def type_convert(df):
    """Coerce date and numeric columns in place (unparseable -> NaT / NaN)."""
    for c in DATE_COLS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.normalize()
    for c in NUMERIC_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def col(df, name):
    """Return a numeric Series for `name`, or an all-NaN series if the column is absent."""
    if name in df.columns:
        return df[name]
    return pd.Series(pd.NA, index=df.index, dtype="float64")


def add_flags(df):
    """Add every quality flag as a boolean column. NaN/NaT operands never flag."""
    cp = col(df, "ClosePrice"); la = col(df, "LivingArea")
    dom = col(df, "DaysOnMarket"); beds = col(df, "BedroomsTotal")
    baths = col(df, "BathroomsTotalInteger"); yb = col(df, "YearBuilt")
    lp = col(df, "ListPrice")

    # (2) invalid-numeric (removal criteria)
    df["invalid_closeprice_flag"] = (cp <= 0).fillna(False)
    df["invalid_livingarea_flag"] = (la <= 0).fillna(False)
    df["negative_dom_flag"] = (dom < 0).fillna(False)
    df["negative_beds_flag"] = (beds < 0).fillna(False)
    df["negative_baths_flag"] = (baths < 0).fillna(False)
    hard = ["invalid_closeprice_flag", "invalid_livingarea_flag", "negative_dom_flag",
            "negative_beds_flag", "negative_baths_flag"]
    df["hard_invalid_flag"] = df[hard].any(axis=1)

    # (3) date consistency (strict '>' so same-day is OK; NaT -> False)
    d_list = col(df, "ListingContractDate"); d_purch = col(df, "PurchaseContractDate")
    d_close = col(df, "CloseDate")
    df["listing_after_close_flag"] = (d_list > d_close).fillna(False)
    df["purchase_after_close_flag"] = (d_purch > d_close).fillna(False)
    df["negative_timeline_flag"] = (
        (d_list > d_purch).fillna(False)
        | (d_purch > d_close).fillna(False)
        | (d_list > d_close).fillna(False))

    # (4) geography
    lat = col(df, "Latitude"); lon = col(df, "Longitude")
    df["missing_coords_flag"] = (lat.isna() | lon.isna())
    df["zero_coord_flag"] = ((lat == 0) | (lon == 0)).fillna(False)
    df["positive_longitude_flag"] = (lon > 0).fillna(False)
    in_ca = lat.between(LAT_MIN, LAT_MAX) & lon.between(LON_MIN, LON_MAX)
    df["out_of_ca_flag"] = (
        (~in_ca) & lat.notna() & lon.notna() & (lat != 0) & (lon != 0))

    # (5) review outliers (non-destructive)
    df["suspicious_low_price_flag"] = ((cp > 0) & (cp < 10_000)).fillna(False)
    df["extreme_high_price_flag"] = (cp > 100_000_000).fillna(False)
    df["extreme_livingarea_flag"] = (la > 25_000).fillna(False)
    df["implausible_yearbuilt_flag"] = ((yb < 1850) | (yb > NEXT_YEAR)).fillna(False)

    # roll-up of every non-removal review flag
    review = ["listing_after_close_flag", "purchase_after_close_flag",
              "negative_timeline_flag", "missing_coords_flag", "zero_coord_flag",
              "positive_longitude_flag", "out_of_ca_flag", "suspicious_low_price_flag",
              "extreme_high_price_flag", "extreme_livingarea_flag",
              "implausible_yearbuilt_flag"]
    df["any_review_flag"] = df[review].any(axis=1)
    return df


def summarize(df, label):
    flag_cols = [c for c in df.columns if c.endswith("_flag")]
    rows = [(c, int(df[c].sum()), round(df[c].mean() * 100, 3)) for c in flag_cols]
    summary = (pd.DataFrame(rows, columns=["flag", "count", "pct"])
               .sort_values("count", ascending=False))
    print(f"\n=== VALIDATION SUMMARY: {label} ({len(df):,} rows) ===")
    print(summary.to_string(index=False))
    return summary


def clean(prefix, in_path):
    print(f"\n########## {prefix.upper()} ##########")
    df = read_any(in_path)
    assert len(df) == EXPECTED_ROWS[prefix], (
        f"{prefix} rows {len(df):,} != expected {EXPECTED_ROWS[prefix]:,}")
    print(f"loaded {len(df):,} rows x {df.shape[1]} cols from {os.path.basename(in_path)}")

    df = type_convert(df)
    present_dates = [c for c in DATE_COLS if c in df.columns]
    print(f"dates converted: {present_dates}")

    df = add_flags(df)
    summarize(df, prefix)

    n_hard = int(df["hard_invalid_flag"].sum())
    clean_view = df[~df["hard_invalid_flag"]].copy()
    print(f"\nhard-invalid rows (removed in clean view): {n_hard:,} "
          f"({n_hard/len(df)*100:.3f}%)")
    print(f"clean-view rows: {len(clean_view):,}  (any_review_flag still present, "
          f"not removed: {int(clean_view['any_review_flag'].sum()):,})")
    assert len(df) == EXPECTED_ROWS[prefix], "flagged output must keep all rows"
    assert len(clean_view) == len(df) - n_hard, "clean-view row math mismatch"

    flagged_out = os.path.join(
        OUTPUT_DIR, f"Week 4-5 _ Deliverable _ {prefix} Residential Cleaned Flagged.csv")
    clean_out = os.path.join(
        OUTPUT_DIR, f"Week 4-5 _ Deliverable _ {prefix} Residential Clean View.csv")
    df.to_csv(flagged_out, index=False)
    clean_view.to_csv(clean_out, index=False)
    print(f"saved flagged -> {os.path.basename(flagged_out)} "
          f"({len(df):,} rows x {df.shape[1]} cols)")
    print(f"saved clean   -> {os.path.basename(clean_out)} ({len(clean_view):,} rows)")
    return prefix, len(df), n_hard, len(clean_view)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = [clean(p, INPUTS[p]) for p in ("Sold", "Listing")]
    print("\n=== CLEANING SUMMARY ===")
    for prefix, n, n_hard, n_clean in results:
        print(f"{prefix:8s}: {n:,} flagged | {n_hard:,} hard-invalid removed "
              f"| {n_clean:,} clean")


if __name__ == "__main__":
    main()


# =============================================================================
# RUN LOG (observed) - 30 months (Jan 2024 - June 2026)
# -----------------------------------------------------------------------------
# SOLD: 455,658 rows -> 51 cols (33 + 18 flags). hard-invalid 209 removed ->
#   clean view 455,449. any_review_flag 54,126 (11.88%).
#   Top flags: missing_coords 53,637 | negative_timeline 405 | invalid_livingarea 161
#   | purchase_after_close 92 | listing_after_close 81 | out_of_ca 65 | negative_dom 48
#   | zero_coord 44 | positive_longitude 34 | extreme_livingarea 15
#   | suspicious_low_price 9 | implausible_yearbuilt 9 | extreme_high_price 2
#   | invalid_closeprice 0 | negative_beds 0 | negative_baths 0
# LISTING: 504,466 rows -> 49 cols. hard-invalid 304 removed -> clean 504,162.
#   any_review_flag 50,086 (9.93%). Top: missing_coords 49,467 | negative_timeline 405
#   | invalid_livingarea 261 | out_of_ca 155 | purchase_after_close 94 | ...
# HEADLINE: missing coordinates (~11.8% sold / ~9.8% listings) is the dominant issue;
#   every other flag is < 0.1%. Hard removals are tiny (<0.07%).
# =============================================================================
