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
    """Median-based segment tables on SOLD (medians: extremes uncapped until Week 7).

    Each table is PRINTED for the check-in and SAVED as a CSV with the same name
    and the same top-10 rows -- the file on disk is exactly the table on screen.
    """
    def seg(by):
        name = by if isinstance(by, str) else " x ".join(by)
        g = df.groupby(by).agg(
            n_sales=("ClosePrice", "size"),
            median_close=("ClosePrice", "median"),
            median_ppsf=("price_per_sqft", "median"),
            median_price_ratio=("price_ratio", "median"),
            median_dom=("days_on_market", "median"),
        ).sort_values("n_sales", ascending=False).head(10).round(2)
        out = os.path.join(OUTPUT_DIR, f"Week 6 _ Segment _ {name}.csv")
        g.to_csv(out)
        print(f"\n-- by {name} (top 10) -- saved -> {os.path.basename(out)}")
        print(g.to_string())

    print("\n=== SEGMENT SUMMARIES (sold, medians) ===")
    print("(PropertyType is 100% 'Residential' post-filter, so segmentation uses "
          "PropertySubType.)")
    for dim in ("PropertySubType", "CountyOrParish", "MLSAreaMajor",
                "ListOfficeName", "BuyerOfficeName"):
        seg(dim)
    # The handbook words this segment as a pair ("CountyOrParish and MLSAreaMajor"),
    # so the combined view is provided too. (PropertyType x PropertySubType would be
    # identical to the PropertySubType table -- PropertyType is constant.)
    seg(["CountyOrParish", "MLSAreaMajor"])
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
#   ranking real offices). Each top-10 table is also saved as
#   "Week 6 _ Segment _ <Dimension>.csv" -- the file is exactly the printed table.
#   Pair segment (handbook wording "CountyOrParish and MLSAreaMajor"): top combo
#   Riverside x Southwest Riverside County 22,648 sales / $587K median -- the
#   single biggest county-area market in the data.
# CROSS-VALIDATION vs teammates: buyer-office counts match bclyman29 to within
#   ~0.1% (NONMEMBER 10,031 identical); their conflated "unmatched" district
#   count (147,693) equals our three separated non-matched buckets summed.
# =============================================================================

# =============================================================================
# OBSERVED OUTPUT -- first 10 rows of each table, verbatim from the run
# -----------------------------------------------------------------------------
# --- Engineered metrics sample (Sold) ---
#  ClosePrice  OriginalListPrice  price_ratio  price_per_sqft    YrMo  listing_to_contract_days  contract_to_close_days  days_on_market
#   5000000.0          5000000.0         1.00         1148.37 2024-01                         0                      63               0
#    858000.0                NaN          NaN          430.08 2024-01                         0                       0               0
#   1890500.0          1890500.0         1.00          591.89 2024-01                         0                       0               0
#   2100000.0          2100000.0         1.00          562.10 2024-01                         0                      48               0
#   2340000.0                NaN          NaN          958.23 2024-01                         0                       0               0
#   1485000.0          1550000.0         0.96          927.55 2024-01                         1                      21               0
#   1130000.0           999000.0         1.13          529.03 2024-01                         1                      17               1
#   1060000.0          1050000.0         1.01          552.95 2024-01                        34                       6              34
# null price_ratio: 937 | null price_per_sqft: 272
#
# -- by PropertySubType (top 10) -- saved -> Week 6 _ Segment _ PropertySubType.csv
#                        n_sales  median_close  median_ppsf  median_price_ratio  median_dom
# PropertySubType                                                                          
# SingleFamilyResidence   340154      882000.0       526.94                1.00        17.0
# Condominium              75830      625000.0       562.17                0.99        24.0
# Townhouse                26621      795000.0       554.49                1.00        18.0
# ManufacturedOnLand        5966      322000.0       225.69                0.97        31.0
# Duplex                    2568      910000.0       541.25                0.98        21.0
# StockCooperative          1793      360000.0       396.53                0.99        21.0
# Cabin                      524      240500.0       287.76                0.92        47.5
# Triplex                    381     1135000.0       466.51                0.97        29.0
# MixedUse                   228      700000.0       449.81                0.93        52.0
# Quadruplex                 159     1275000.0       376.95                0.95        34.0
#
# -- by CountyOrParish (top 10) -- saved -> Week 6 _ Segment _ CountyOrParish.csv
#                 n_sales  median_close  median_ppsf  median_price_ratio  median_dom
# CountyOrParish                                                                    
# Los Angeles      113426      900000.0       608.47                1.00        19.0
# Riverside         64221      600000.0       320.73                0.99        30.0
# San Diego         58531      895000.0       589.30                0.99        15.0
# Orange            51112     1180000.0       673.50                0.99        14.0
# San Bernardino    42636      534900.0       331.88                0.99        25.0
# Alameda           21474     1125000.0       697.28                1.02        14.0
# Contra Costa      21382      819000.0       519.11                1.00        14.0
# Santa Clara       16635     1540000.0       944.68                1.02        10.0
# Ventura           14445      865000.0       516.55                0.99        28.0
# San Mateo          6876     1650000.0      1035.80                1.01        12.0
#
# -- by MLSAreaMajor (top 10) -- saved -> Week 6 _ Segment _ MLSAreaMajor.csv
#                                       n_sales  median_close  median_ppsf  median_price_ratio  median_dom
# MLSAreaMajor                                                                                            
# 699 - Not Defined                       41783     1150000.0       743.56                1.00        13.0
# SRCAR - Southwest Riverside County      22656      587000.0       293.16                1.00        24.0
# 252 - Riverside                          5884      656000.0       378.04                1.00        21.0
# 248 - Corona                             3724      757250.0       396.37                0.99        22.0
# LAC - Lancaster                          3448      475000.0       270.83                1.00        25.0
# 263 - Banning/Beaumont/Cherry Valley     3263      499999.0       259.92                0.99        30.0
# VIC - Victorville                        3243      438000.0       237.96                1.00        24.0
# 274 - San Bernardino                     3176      500000.0       352.92                1.00        21.0
# 259 - Moreno Valley                      2942      555000.0       311.99                1.00        18.0
# 686 - Ontario                            2925      651990.0       416.67                1.00        20.0
#
# -- by ListOfficeName (top 10) -- saved -> Week 6 _ Segment _ ListOfficeName.csv
#                                                        n_sales  median_close  median_ppsf  median_price_ratio  median_dom
# ListOfficeName                                                                                                           
# Compass                                                  31822     1330000.0       748.13                1.00        14.0
# Coldwell Banker Realty                                   19936     1163000.0       683.08                0.99        16.0
# Keller Williams Realty                                    9013      870000.0       539.48                1.00        15.0
# First Team Real Estate                                    6342      960000.0       608.00                1.00        13.0
# Berkshire Hathaway HomeServices California Properties     5918      950000.0       598.31                0.98        23.0
# Real Broker                                               5436      845000.0       556.18                1.00        15.0
# eXp Realty of California Inc                              5286      780000.0       524.93                1.00        19.0
# Intero Real Estate Services                               4253     1312000.0       816.58                1.01        12.0
# eXp Realty of California, Inc.                            4045      755000.0       492.99                1.00        13.0
# Equity Union                                              3963      850000.0       474.77                0.98        28.0
#
# -- by BuyerOfficeName (top 10) -- saved -> Week 6 _ Segment _ BuyerOfficeName.csv
#                                                        n_sales  median_close  median_ppsf  median_price_ratio  median_dom
# BuyerOfficeName                                                                                                          
# Compass                                                  29804     1310167.5       744.87                1.00        15.0
# Coldwell Banker Realty                                   16044     1165000.0       678.81                0.99        16.0
# NONMEMBER MRML                                           10031      500000.0       288.64                0.99        26.0
# Keller Williams Realty                                    7133      834000.0       532.11                1.00        17.0
# Real Broker                                               7043      800000.0       542.61                1.00        18.0
# eXp Realty of California Inc                              5753      825000.0       566.16                1.00        19.0
# First Team Real Estate                                    5753      899900.0       595.91                1.00        14.0
# eXp Realty of California, Inc.                            5278      725000.0       494.08                1.00        18.0
# Berkshire Hathaway HomeServices California Properties     4605      982000.0       609.32                0.99        21.0
# Redfin Corporation                                        3713      840000.0       540.47                0.99        20.0
#
# -- by CountyOrParish x MLSAreaMajor (top 10) -- saved -> Week 6 _ Segment _ CountyOrParish x MLSAreaMajor.csv
#                                                      n_sales  median_close  median_ppsf  median_price_ratio  median_dom
# CountyOrParish MLSAreaMajor                                                                                            
# Riverside      SRCAR - Southwest Riverside County      22648      587028.0       293.21                1.00        24.0
# Santa Clara    699 - Not Defined                       15142     1552750.0       953.64                1.02        10.0
# San Mateo      699 - Not Defined                        6367     1700000.0      1048.61                1.01        12.0
# Riverside      252 - Riverside                          5884      656000.0       378.04                1.00        21.0
# Monterey       699 - Not Defined                        4022      905000.0       591.88                0.98        19.0
# Riverside      248 - Corona                             3723      757500.0       396.37                0.99        22.0
# Los Angeles    LAC - Lancaster                          3448      475000.0       270.83                1.00        25.0
# Riverside      263 - Banning/Beaumont/Cherry Valley     3263      499999.0       259.92                0.99        30.0
# San Bernardino VIC - Victorville                        3243      438000.0       237.96                1.00        24.0
#                274 - San Bernardino                     3174      500000.0       353.02                1.00        21.0
# =============================================================================
