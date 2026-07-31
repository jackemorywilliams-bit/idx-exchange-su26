"""
Week 6 Deliverable - Feature Engineering and Market Metrics.

Input: the Weeks 4-5 SOLD clean view (455,449 rows; hard numeric errors removed,
review flags kept as 0/1). All metrics are engineered on this one dataset -- every
price metric needs ClosePrice, so the sold side is the analysis base.

ENGINEERED COLUMNS
  price_ratio                   ClosePrice / OriginalListPrice  (negotiation strength)
  close_to_original_list_ratio  same formula -- the handbook lists BOTH metrics with
                                the identical definition, so both column names are
                                provided from one computation (no pretense of
                                independent logic)
  price_per_sqft                ClosePrice / LivingArea
  Year / Month / YrMo           from CloseDate (ints + 'YYYY-MM' string; CloseDate
                                itself stays datetime -- Tableau's native date field)
  listing_to_contract_days      PurchaseContractDate - ListingContractDate
  contract_to_close_days        CloseDate - PurchaseContractDate
  DistrictName                  Unified school district containing the property
                                (spatial join; see below)
  district_match_status         matched / no_unified_district / invalid_coords /
                                missing_coords  (so a null DistrictName is never
                                mistaken for data loss)

METRIC DICTIONARY (definitions locked here so Week 8-12 dashboards reconcile):
  - "Avg DOM" on dashboards = the CRMLS system field DaysOnMarket (kept as-is; it is
    NOT CloseDate - ListingContractDate, which matches it on only ~55% of rows).
  - Ratio dashboards = AVG of row-level price_ratio (not ratio of aggregates).
  - price_ratio is a decimal (0.98); format as % in Tableau, never pre-multiplied.
  - Durations are integer days; negatives are retained (those rows carry
    negative_timeline_flag=1 -- filter on the flag, don't silently drop).
  - Office-name variants (e.g. two spellings of eXp / Redfin) are NOT normalized here
    (cleaning, not feature engineering). For Week 9's top-100 offices, use
    office_key = UPPER(TRIM(collapse whitespace(name))) as the starting recipe.

SCHOOL-DISTRICT SPATIAL JOIN (per program instructions)
  Source: California School District Areas 2025-26 (data.ca.gov), 936 districts.
  Filtered to DistrictType == 'Unified' (345 polygons). The source file is
  EPSG:3857 and is reprojected to EPSG:4326 before joining; property points are
  built from (Longitude, Latitude) in 4326. Join = left sjoin, predicate 'within'.
  Only rows with trustworthy coordinates are joined: rows flagged missing / zero-
  sentinel / positive-longitude / outside-CA are excluded up front and labeled in
  district_match_status instead. Valid points matching no Unified polygon are
  EXPECTED (much of CA is served by separate elementary + high districts).

COVERAGE CAVEAT for any district-level view: district figures cover geocoded sales
only (~88%); the missing 12% is non-random (2024-heavy, Bay-Area-heavy, pricier),
so affected districts undercount volume and skew price stats low.
"""

import os

import geopandas as gpd
import pandas as pd

# --- Configuration -----------------------------------------------------------
DELIV = os.path.expanduser(os.environ.get(
    "CRMLS_DELIV_DIR", "~/idx-exchange/deliverables"))
OUTPUT_DIR = os.path.expanduser(os.environ.get("CRMLS_OUTPUT_DIR", DELIV))

SOLD_IN = os.path.join(DELIV, "Week 4-5 _ Deliverable _ Sold Residential Clean View.csv")
DISTRICTS_IN = os.path.expanduser("~/idx-exchange/data/ca_school_districts_2025_26.geojson")
SOLD_OUT = os.path.join(OUTPUT_DIR, "Week 6 _ Deliverable _ Sold Residential Enriched.csv")

EXPECTED_ROWS = 455_449
DATE_COLS = ["ListingContractDate", "PurchaseContractDate", "CloseDate"]


def load_sold():
    df = pd.read_csv(SOLD_IN, low_memory=False)
    assert len(df) == EXPECTED_ROWS, f"rows {len(df):,} != expected {EXPECTED_ROWS:,}"
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    print(f"loaded sold clean view: {len(df):,} rows x {df.shape[1]} cols")
    return df


def engineer_metrics(df):
    """Add every handbook metric. NaN where undefined; no caps (Week 7 = outliers)."""
    olp = df["OriginalListPrice"].where(df["OriginalListPrice"] > 0)  # 0 -> NaN, no inf
    la = df["LivingArea"].where(df["LivingArea"] > 0)

    df["price_ratio"] = df["ClosePrice"] / olp
    df["close_to_original_list_ratio"] = df["price_ratio"]  # identical by handbook definition
    df["price_per_sqft"] = df["ClosePrice"] / la

    df["Year"] = df["CloseDate"].dt.year.astype("Int64")
    df["Month"] = df["CloseDate"].dt.month.astype("Int64")
    df["YrMo"] = df["CloseDate"].dt.strftime("%Y-%m")

    # Negative durations are retained: those rows carry negative_timeline_flag=1.
    df["listing_to_contract_days"] = (
        (df["PurchaseContractDate"] - df["ListingContractDate"]).dt.days.astype("Int64"))
    df["contract_to_close_days"] = (
        (df["CloseDate"] - df["PurchaseContractDate"]).dt.days.astype("Int64"))

    print("\n=== ENGINEERED METRICS -- sample (new columns populated) ===")
    sample_cols = ["ClosePrice", "OriginalListPrice", "price_ratio", "price_per_sqft",
                   "YrMo", "listing_to_contract_days", "contract_to_close_days",
                   "DaysOnMarket"]
    print(df[sample_cols].head(8).round(2).to_string(index=False))

    n_neg = int((df["listing_to_contract_days"] < 0).sum()
                + (df["contract_to_close_days"] < 0).sum())
    print(f"\nnull price_ratio: {int(df['price_ratio'].isna().sum()):,} "
          f"(OriginalListPrice missing/zero) | null price_per_sqft: "
          f"{int(df['price_per_sqft'].isna().sum()):,} (LivingArea missing)")
    print(f"negative duration values retained (rows are timeline-flagged): {n_neg:,}")
    print("note: handbook defines Price Ratio and Close-to-Original-List Ratio with "
          "the same formula; both columns are provided from one computation.")
    return df


def join_school_districts(df):
    """Left spatial join of trustworthy property points onto Unified districts."""
    gdf = gpd.read_file(DISTRICTS_IN)
    print(f"\n=== SCHOOL-DISTRICT JOIN ===")
    print(f"district file: {len(gdf)} districts | crs {gdf.crs} | "
          f"types {gdf['DistrictType'].value_counts().to_dict()}")
    unified = gdf[gdf["DistrictType"] == "Unified"][["DistrictName", "geometry"]]
    unified = unified.to_crs("EPSG:4326")
    print(f"unified districts kept: {len(unified)}")

    # Trustworthy coordinates only: geographic flags exclude rows up front.
    bad_geo = (df["missing_coords_flag"].eq(1) | df["zero_coord_flag"].eq(1)
               | df["positive_longitude_flag"].eq(1) | df["out_of_ca_flag"].eq(1))
    valid = df[~bad_geo]
    pts = gpd.GeoDataFrame(
        valid[[]],
        geometry=gpd.points_from_xy(valid["Longitude"], valid["Latitude"],
                                    crs="EPSG:4326"))
    assert pts.crs == unified.crs
    joined = gpd.sjoin(pts, unified, how="left", predicate="within")

    # A point exactly on a shared boundary could match twice -- dedup deterministically.
    n_dup = int(joined.index.duplicated().sum())
    if n_dup:
        joined = (joined.sort_values("DistrictName")
                        .loc[~joined.index.duplicated(keep="first")])
    print(f"boundary double-matches deduped: {n_dup}")

    df["DistrictName"] = joined["DistrictName"]
    df["district_match_status"] = "matched"
    df.loc[df["DistrictName"].isna(), "district_match_status"] = "no_unified_district"
    df.loc[bad_geo & df["zero_coord_flag"].eq(0) & df["missing_coords_flag"].eq(0),
           "district_match_status"] = "invalid_coords"
    df.loc[df["zero_coord_flag"].eq(1), "district_match_status"] = "invalid_coords"
    df.loc[df["missing_coords_flag"].eq(1), "district_match_status"] = "missing_coords"

    # Coverage report (four-way; buckets 2 and 3 are different things).
    print("\ncoverage (of all rows):")
    cov = df["district_match_status"].value_counts()
    for k, v in cov.items():
        print(f"  {k:20s} {v:8,}  ({v/len(df)*100:5.2f}%)")
    n_valid = len(valid)
    n_match = int((df["district_match_status"] == "matched").sum())
    print(f"match rate among valid-coordinate rows: {n_match/n_valid*100:.1f}% "
          f"(expected ~70-85%; much of CA is elementary+high territory)")

    # --- Validation: positive + negative spot checks, distribution plausibility ---
    print("\nvalidation spot-checks (city -> modal district):")
    for city, expect in [("Irvine", "Irvine Unified"), ("San Diego", "San Diego Unified"),
                         ("Long Beach", "Long Beach Unified"),
                         ("Santa Ana", "Santa Ana Unified")]:
        got = (df.loc[(df["City"] == city) & df["DistrictName"].notna(),
                      "DistrictName"].mode())
        got = got.iloc[0] if len(got) else "NO MATCHES"
        print(f"  {city:10s} -> {got}   {'OK' if got == expect else '** CHECK **'}")
    cup = df.loc[df["City"] == "Cupertino", "district_match_status"].value_counts()
    print(f"  negative control -- Cupertino (elem+high territory): {cup.to_dict()}")

    print("\ntop 10 unified districts by sales:")
    print(df["DistrictName"].value_counts().head(10).to_string())
    print("\nper-county match rate (top 6 by sales) -- pre-verifies report geography:")
    top_cty = df["CountyOrParish"].value_counts().head(6).index
    for cty in top_cty:
        sub = df[df["CountyOrParish"] == cty]
        print(f"  {cty:15s} matched {(sub['district_match_status'] == 'matched').mean()*100:5.1f}%"
              f" | missing coords {(sub['district_match_status'] == 'missing_coords').mean()*100:5.1f}%")
    return df


def segment_summaries(df):
    """Median-based segment tables (medians: extremes are uncapped until Week 7)."""
    def seg(by, top=None):
        g = df.groupby(by).agg(
            n_sales=("ClosePrice", "size"),
            median_close=("ClosePrice", "median"),
            median_ppsf=("price_per_sqft", "median"),
            median_price_ratio=("price_ratio", "median"),
            median_dom=("DaysOnMarket", "median"),
        ).sort_values("n_sales", ascending=False)
        return g.head(top) if top else g

    print("\n=== SEGMENT SUMMARIES (medians) ===")
    print("(PropertyType is 100% 'Residential' post-filter, so segmentation uses "
          "PropertySubType; MLSAreaMajor available but too high-cardinality to print.)")
    print("\n-- by PropertySubType (top 10) --")
    print(seg("PropertySubType", 10).round(2).to_string())
    print("\n-- by CountyOrParish (top 10) --")
    print(seg("CountyOrParish", 10).round(2).to_string())
    print("\n-- by ListOfficeName (top 10 by volume) --")
    print(seg("ListOfficeName", 10).round(2).to_string())
    print("\ncaveat: office totals are split across variant spellings (e.g. eXp, "
          "Redfin each appear twice); normalization is deferred to the Week 9 "
          "top-100 build (see metric dictionary).")


def main():
    df = load_sold()
    df = engineer_metrics(df)
    df = join_school_districts(df)
    segment_summaries(df)

    assert len(df) == EXPECTED_ROWS, "row count must be unchanged"
    df.to_csv(SOLD_OUT, index=False)
    print(f"\nsaved enriched dataset -> {os.path.basename(SOLD_OUT)} "
          f"({len(df):,} rows x {df.shape[1]} cols)")


if __name__ == "__main__":
    main()


# =============================================================================
# RUN LOG (observed) - sold clean view, 455,449 rows -> enriched 455,449 x 61 cols
# -----------------------------------------------------------------------------
# METRICS: null price_ratio 937 (OLP missing/zero) | null PPSF 272 (LivingArea NaN)
#   | negative durations retained 405 (all timeline-flagged)
# DISTRICT JOIN (936 districts, 345 Unified, EPSG:3857 -> 4326):
#   matched 307,683 (67.56%) | no_unified_district 94,032 (20.65%)
#   | missing_coords 53,625 (11.77%) | invalid_coords 109 (0.02%)
#   match rate among valid-coord rows: 76.6% (expected band 70-85%)
#   spot checks: Irvine/San Diego/Long Beach/Santa Ana -> their Unified OK;
#   Cupertino negative control -> 0 false matches. Top district: LA Unified 44,613.
#   Per-county match rate: Riverside BEST at 84.3% matched / 5.6% missing coords
#   (LA 79.5%/5.8%, Orange 71.3%, San Bernardino 70.3%, San Diego 50.7%,
#    Alameda 71.2% but 28.6% missing) -- strengthens Riverside as the Week 11-12
#   report geography.
# SEGMENTS: SFR median $882K/17d | Condo $625K/24d; county medians from
#   San Bernardino $535K to San Mateo $1.65M; office table caveated (name variants).
# =============================================================================
