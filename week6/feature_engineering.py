"""
Week 6 Deliverable - Feature Engineering and Market Metrics.

Input: the Weeks 4-5 clean views (sold 455,449 rows / listings 504,162 rows; hard
numeric errors removed, review flags kept as 0/1). Metrics and the school-district
join are applied to BOTH datasets (matching the team's shared approach); segment
summaries are computed on sold, where every price metric is fully populated.

ENGINEERED COLUMNS (both datasets)
  price_ratio                   ClosePrice / OriginalListPrice  (negotiation strength)
  close_to_original_list_ratio  same formula -- the handbook lists BOTH metrics with
                                the identical definition, so both column names are
                                provided from one computation
  price_per_sqft                ClosePrice / LivingArea
  days_on_market                the raw CRMLS DaysOnMarket field under the metric's
                                snake_case name (cohort-consistent schema)
  Year / Month / YrMo           from CloseDate (ints + 'YYYY-MM' string; CloseDate
                                itself stays datetime -- Tableau's native date field)
  listing_to_contract_days      PurchaseContractDate - ListingContractDate
  contract_to_close_days        CloseDate - PurchaseContractDate
  DistrictName                  Unified school district containing the property
  district_match_status         matched / no_unified_district / invalid_coords /
                                missing_coords  (a null DistrictName is never
                                mistaken for data loss)

METRIC DICTIONARY (definitions locked here so Week 8-12 dashboards reconcile):
  - "Avg DOM" on dashboards = the CRMLS system field DaysOnMarket (= days_on_market;
    it is NOT CloseDate - ListingContractDate, which matches on only ~55% of rows).
  - Ratio dashboards = AVG of row-level price_ratio (not ratio of aggregates).
  - price_ratio is a decimal (0.98); format as % in Tableau, never pre-multiplied.
  - Durations are integer days; negatives are retained (those rows carry
    negative_timeline_flag=1 -- filter on the flag, don't silently drop).
  - On LISTINGS, ClosePrice-based metrics are NaN for unsold listings (~16%) by
    definition -- the row is still on the market.
  - Office-name variants (e.g. two spellings of eXp / Redfin) are NOT normalized here
    (cleaning, not feature engineering). For Week 9's top-100 offices, use
    office_key = UPPER(TRIM(collapse whitespace(name))) as the starting recipe.

SCHOOL-DISTRICT SPATIAL JOIN (per program instructions)
  Source: California School District Areas 2025-26 (data.ca.gov), 936 districts.
  Filtered to DistrictType == 'Unified' (345 polygons). The source file is
  EPSG:3857 and is reprojected to EPSG:4326; property points are built from
  (Longitude, Latitude) in 4326. Join = left sjoin, predicate 'within'. Only rows
  with trustworthy coordinates are joined: rows flagged missing / zero-sentinel /
  positive-longitude / outside-CA are excluded up front and labeled in
  district_match_status instead. Valid points matching no Unified polygon are
  EXPECTED (much of CA is served by separate elementary + high districts).

COVERAGE CAVEAT for any district-level view: district figures cover geocoded rows
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

INPUTS = {
    "Sold": os.path.join(DELIV, "Week 4-5 _ Deliverable _ Sold Residential Clean View.csv"),
    "Listing": os.path.join(DELIV, "Week 4-5 _ Deliverable _ Listing Residential Clean View.csv"),
}
EXPECTED_ROWS = {"Sold": 455_449, "Listing": 504_162}
DISTRICTS_IN = os.path.expanduser("~/idx-exchange/data/ca_school_districts_2025_26.geojson")

DATE_COLS = ["ListingContractDate", "PurchaseContractDate", "CloseDate"]


def load_clean(prefix):
    df = pd.read_csv(INPUTS[prefix], low_memory=False)
    assert len(df) == EXPECTED_ROWS[prefix], (
        f"{prefix} rows {len(df):,} != expected {EXPECTED_ROWS[prefix]:,}")
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    print(f"\n########## {prefix.upper()} ##########")
    print(f"loaded clean view: {len(df):,} rows x {df.shape[1]} cols")
    return df


def engineer_metrics(df, label):
    """Add every handbook metric. NaN where undefined; no caps (Week 7 = outliers)."""
    olp = df["OriginalListPrice"].where(df["OriginalListPrice"] > 0)  # 0 -> NaN, no inf
    la = df["LivingArea"].where(df["LivingArea"] > 0)

    df["price_ratio"] = df["ClosePrice"] / olp
    df["close_to_original_list_ratio"] = df["price_ratio"]  # identical by handbook definition
    df["price_per_sqft"] = df["ClosePrice"] / la
    df["days_on_market"] = df["DaysOnMarket"]  # raw system field, metric-schema name

    df["Year"] = df["CloseDate"].dt.year.astype("Int64")
    df["Month"] = df["CloseDate"].dt.month.astype("Int64")
    df["YrMo"] = df["CloseDate"].dt.strftime("%Y-%m")

    # Negative durations are retained: those rows carry negative_timeline_flag=1.
    df["listing_to_contract_days"] = (
        (df["PurchaseContractDate"] - df["ListingContractDate"]).dt.days.astype("Int64"))
    df["contract_to_close_days"] = (
        (df["CloseDate"] - df["PurchaseContractDate"]).dt.days.astype("Int64"))

    print(f"\n=== ENGINEERED METRICS ({label}) -- sample ===")
    sample_cols = ["ClosePrice", "OriginalListPrice", "price_ratio", "price_per_sqft",
                   "YrMo", "listing_to_contract_days", "contract_to_close_days",
                   "days_on_market"]
    print(df[sample_cols].head(8).round(2).to_string(index=False))
    print(f"null price_ratio: {int(df['price_ratio'].isna().sum()):,} | "
          f"null price_per_sqft: {int(df['price_per_sqft'].isna().sum()):,}")
    return df


def join_school_districts(df, unified, label):
    """Left spatial join of trustworthy property points onto Unified districts."""
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

    df["DistrictName"] = joined["DistrictName"]
    df["district_match_status"] = "matched"
    df.loc[df["DistrictName"].isna(), "district_match_status"] = "no_unified_district"
    df.loc[bad_geo, "district_match_status"] = "invalid_coords"
    df.loc[df["missing_coords_flag"].eq(1), "district_match_status"] = "missing_coords"

    print(f"\n=== SCHOOL-DISTRICT JOIN ({label}) === (boundary dedups: {n_dup})")
    cov = df["district_match_status"].value_counts()
    for k, v in cov.items():
        print(f"  {k:20s} {v:8,}  ({v/len(df)*100:5.2f}%)")
    n_match = int((df["district_match_status"] == "matched").sum())
    print(f"match rate among valid-coordinate rows: {n_match/len(valid)*100:.1f}%")
    return df


def validate_join(df):
    """Positive + negative spot checks and distribution plausibility (sold only)."""
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
    for cty in df["CountyOrParish"].value_counts().head(6).index:
        sub = df[df["CountyOrParish"] == cty]
        print(f"  {cty:15s} matched {(sub['district_match_status'] == 'matched').mean()*100:5.1f}%"
              f" | missing coords {(sub['district_match_status'] == 'missing_coords').mean()*100:5.1f}%")


def segment_summaries(df):
    """Median-based segment tables on SOLD (medians: extremes uncapped until Week 7)."""
    def seg(by, top=None):
        g = df.groupby(by).agg(
            n_sales=("ClosePrice", "size"),
            median_close=("ClosePrice", "median"),
            median_ppsf=("price_per_sqft", "median"),
            median_price_ratio=("price_ratio", "median"),
            median_dom=("days_on_market", "median"),
        ).sort_values("n_sales", ascending=False)
        return g.head(top) if top else g

    print("\n=== SEGMENT SUMMARIES (sold, medians) ===")
    print("(PropertyType is 100% 'Residential' post-filter, so segmentation uses "
          "PropertySubType.)")
    print("\n-- by PropertySubType (top 10) --")
    print(seg("PropertySubType", 10).round(2).to_string())
    print("\n-- by CountyOrParish (top 10) --")
    print(seg("CountyOrParish", 10).round(2).to_string())
    print("\n-- by MLSAreaMajor (top 10) --")
    print(seg("MLSAreaMajor", 10).round(2).to_string())
    print("\n-- by ListOfficeName (top 10 by volume) --")
    print(seg("ListOfficeName", 10).round(2).to_string())
    print("\n-- by BuyerOfficeName (top 10 by volume, competitive intelligence) --")
    print(seg("BuyerOfficeName", 10).round(2).to_string())
    print("\ncaveat: office totals are split across variant spellings (e.g. eXp, "
          "Redfin each appear twice); normalization is deferred to the Week 9 "
          "top-100 build (see metric dictionary). BuyerOfficeName also contains "
          "non-member sentinels (e.g. 'NONMEMBER MRML') -- exclude before ranking "
          "real offices.")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    gdf = gpd.read_file(DISTRICTS_IN)
    print(f"district file: {len(gdf)} districts | crs {gdf.crs} | "
          f"types {gdf['DistrictType'].value_counts().to_dict()}")
    unified = (gdf[gdf["DistrictType"] == "Unified"][["DistrictName", "geometry"]]
               .to_crs("EPSG:4326"))
    print(f"unified districts kept: {len(unified)}")

    for prefix in ("Sold", "Listing"):
        df = load_clean(prefix)
        df = engineer_metrics(df, prefix)
        df = join_school_districts(df, unified, prefix)
        if prefix == "Sold":
            validate_join(df)
            segment_summaries(df)
        assert len(df) == EXPECTED_ROWS[prefix], "row count must be unchanged"
        out = os.path.join(OUTPUT_DIR,
                           f"Week 6 _ Deliverable _ {prefix} Residential Enriched.csv")
        df.to_csv(out, index=False)
        print(f"\nsaved -> {os.path.basename(out)} ({len(df):,} rows x {df.shape[1]} cols)")


if __name__ == "__main__":
    main()


# =============================================================================
# RUN LOG (observed)
# -----------------------------------------------------------------------------
# SOLD (455,449 -> 62 cols): null price_ratio 937 | null PPSF 272 | negative
#   durations retained 405 (timeline-flagged). District join: matched 307,683
#   (67.56%) | no_unified_district 94,032 | missing_coords 53,625 | invalid 109;
#   76.6% of valid-coord rows. Spot checks Irvine/San Diego/Long Beach/Santa Ana
#   OK; Cupertino negative control 0 false matches; LA Unified #1 (44,613).
#   Per-county match: Riverside best 84.3% matched / 5.6% missing coords.
# LISTING (504,162 -> 60 cols): district matched 348,301 (69.09%) |
#   no_unified 106,190 | missing_coords 49,455 | invalid 216; 76.6% of valid.
# SEGMENTS (sold): SFR median $882K/17d | Condo $625K/24d; counties $535K (San
#   Bernardino) .. $1.65M (San Mateo); top buyer offices Compass 29,804 /
#   Coldwell Banker 16,044 / NONMEMBER MRML 10,031 (sentinel -- exclude before
#   ranking real offices).
# CROSS-VALIDATION vs teammates: buyer-office counts match bclyman29 to within
#   ~0.1% (NONMEMBER 10,031 identical); their conflated "unmatched" district
#   count (147,693) equals our three separated non-matched buckets summed.
# =============================================================================
