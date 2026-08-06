"""
Week 7 Deliverable - Outlier Detection and Data Quality (IQR method).

SPEC CHECKLIST (handbook wording -> artifact):
  "a .py script applying IQR filtering"        -> this script; Q1/Q3, IQR=Q3-Q1,
                                                  fences = Q1-1.5*IQR / Q3+1.5*IQR
  "key numeric fields (ClosePrice,
   LivingArea, DaysOnMarket)"                  -> exactly these three, both datasets
  "Add outlier flag columns rather than
   deleting records outright"                  -> 0/1 flags; flagged outputs keep
                                                  every row (counts asserted)
  "Save both a full flagged dataset and a
   clean filtered dataset"                     -> 4 CSVs: {Sold,Listing} x
                                                  {IQR Flagged, IQR Filtered}
  "a written comparison of dataset size and
   median values before and after filtering"   -> printed comparison table below
                                                  (+ README prose)
  "use percentiles alongside IQR"              -> percentile block printed per field

Inputs: the Week 6 enriched datasets (sold 455,449 x 62 / listings 504,162 x 60).
DistrictName / district_match_status and all engineered metrics carry through to
every output (asserted + printed) -- the school-district mapping itself was done
in Week 6 and is only confirmed here, not redone.

Rules (council):
  - Fences computed per dataset on NON-NULL values of each field. A null value
    never flags (missingness is a completeness issue, not an outlier), so the
    ~16% of listings with no ClosePrice pass the price fence vacuously and stay.
  - All three fences are effectively upper-only (lower fences go negative on
    right-skewed data) -- expected, reported, not "fixed".
  - Quantiles are computed on all rows as-is: quartiles have ~25% breakdown
    points, so surviving extremes cannot meaningfully move them.
  - Sanity band: total any-flag share should land ~12-20%; outside 5-30% = bug.

PROVENANCE (three copies: here, printed banner, README):
  The FILTERED files are for GENERAL MARKET-TREND charts only. All investor /
  flip / agent / sentinel capstone metrics use the FLAGGED (pre-IQR) files --
  locked council ruling. The DOM fence in particular removes stale listings,
  which are the acquisition channel of the flip signal.
"""

import os

import pandas as pd

# --- Configuration -----------------------------------------------------------
DELIV = os.path.expanduser(os.environ.get(
    "CRMLS_DELIV_DIR", "~/idx-exchange/deliverables"))
OUTPUT_DIR = os.path.expanduser(os.environ.get("CRMLS_OUTPUT_DIR", DELIV))

INPUTS = {
    "Sold": os.path.join(DELIV, "Week 6 _ Deliverable _ Sold Residential Enriched.csv"),
    "Listing": os.path.join(DELIV, "Week 6 _ Deliverable _ Listing Residential Enriched.csv"),
}
EXPECTED_ROWS = {"Sold": 455_449, "Listing": 504_162}

IQR_FIELDS = ["ClosePrice", "LivingArea", "DaysOnMarket"]
FLAG_OF = {"ClosePrice": "closeprice_iqr_outlier_flag",
           "LivingArea": "livingarea_iqr_outlier_flag",
           "DaysOnMarket": "daysonmarket_iqr_outlier_flag"}
PCTS = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]


def read_any(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="cp1252")


PREVIEW_COLS = ["ClosePrice", "LivingArea", "DaysOnMarket", "YrMo", "CountyOrParish"]


def preview(df, label, extra_cols=()):
    """Small .head() table at each stage so the run is easy to talk through."""
    cols = PREVIEW_COLS + [c for c in extra_cols if c in df.columns]
    print(f"\n-- preview: {label} (first 5 rows) --")
    print(df[cols].head(5).to_string(index=False))


def iqr_flags(df, label):
    """Percentile evidence + IQR fences + one 0/1 flag per field + rollup."""
    for f in IQR_FIELDS:
        df[f] = pd.to_numeric(df[f], errors="coerce")
        assert FLAG_OF[f] not in df.columns, f"flag name collision: {FLAG_OF[f]}"

    print(f"\n=== IQR FENCES & PERCENTILES ({label}) ===")
    for f in IQR_FIELDS:
        s = df[f].dropna()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        below, above = int((s < lo).sum()), int((s > hi).sum())
        pct_line = "  ".join(f"p{int(p*100)}={s.quantile(p):,.0f}" for p in PCTS)
        print(f"\n{f}: n={len(s):,} (non-null)  min={s.min():,.0f}  max={s.max():,.0f}")
        print(f"  {pct_line}")
        print(f"  Q1={q1:,.0f}  Q3={q3:,.0f}  IQR={iqr:,.0f}  "
              f"fences=[{lo:,.1f}, {hi:,.1f}]")
        print(f"  flagged: below={below:,}  above={above:,}  total={below+above:,} "
              f"({(below+above)/len(df)*100:.2f}% of rows)")
        # NaN comparisons are False, so null values never flag -- by design.
        df[FLAG_OF[f]] = ((df[f] < lo) | (df[f] > hi)).astype("int8")

    df["any_iqr_outlier_flag"] = (
        df[list(FLAG_OF.values())].any(axis=1).astype("int8"))
    share = df["any_iqr_outlier_flag"].mean() * 100
    print(f"\nany_iqr_outlier_flag: {int(df['any_iqr_outlier_flag'].sum()):,} rows "
          f"({share:.2f}%)")
    assert 5 <= share <= 30, f"any-flag share {share:.1f}% outside sanity band -- bug?"
    return df


def written_comparison(before, after, label):
    """The handbook's written comparison: size + medians (means as context)."""
    print(f"\n=== WRITTEN COMPARISON ({label}): before vs after IQR filtering ===")
    rows = []
    for name, d in [("before (flagged, all rows)", before), ("after (filtered)", after)]:
        rows.append({
            "dataset": name, "rows": len(d),
            "median_ClosePrice": d["ClosePrice"].median(),
            "mean_ClosePrice": round(d["ClosePrice"].mean(), 0),
            "median_LivingArea": d["LivingArea"].median(),
            "median_DOM": d["DaysOnMarket"].median(),
        })
    cmp_df = pd.DataFrame(rows).set_index("dataset")
    print(cmp_df.to_string())
    removed = len(before) - len(after)
    print(f"rows removed by filter: {removed:,} ({removed/len(before)*100:.2f}%) | "
          f"retained: {len(after)/len(before)*100:.2f}%")
    return cmp_df


def capstone_measurements(df):
    """Three cheap crosstabs (sold): does the filter skew geography / investor tier?"""
    print("\n=== FILTER-SKEW MEASUREMENTS (sold) ===")
    print("any-flag rate by county (top 6 by sales):")
    for cty in df["CountyOrParish"].value_counts().head(6).index:
        sub = df[df["CountyOrParish"] == cty]
        print(f"  {cty:15s} {sub['any_iqr_outlier_flag'].mean()*100:5.1f}% flagged")

    tier = df[df["ClosePrice"] < 600_000]
    print(f"\nsub-$600K (investor-tier) stock: {len(tier):,} rows | "
          f"any-flag {tier['any_iqr_outlier_flag'].mean()*100:.1f}% "
          f"(price fence cannot fire here; drivers below)")
    for f, flag in FLAG_OF.items():
        print(f"  {f:12s} fence fired on {int(tier[flag].sum()):,} "
              f"({tier[flag].mean()*100:.1f}%)")

    slow = df[df["daysonmarket_iqr_outlier_flag"] == 1]
    nonmember = slow["BuyerOfficeName"].str.contains("NONMEMBER|NONE MRML",
                                                     case=False, na=False)
    print(f"\nDOM-fence tail (slow sales, {len(slow):,} rows): "
          f"{(slow['ClosePrice'] < 600_000).mean()*100:.1f}% sub-$600K | "
          f"{(slow['CountyOrParish'] == 'Riverside').mean()*100:.1f}% Riverside | "
          f"{nonmember.mean()*100:.1f}% NONMEMBER-buyer")


def confirm_carry_through(df, label):
    """District + engineered columns survive into outputs (school-district check)."""
    for col in ("DistrictName", "district_match_status", "price_ratio",
                "price_per_sqft", "YrMo", "listing_to_contract_days",
                "contract_to_close_days"):
        assert col in df.columns, f"{label}: lost upstream column {col}"
    print(f"\ndistrict_match_status carry-through ({label}):")
    print(df["district_match_status"].value_counts().to_string())


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for prefix in ("Sold", "Listing"):
        print(f"\n########## {prefix.upper()} ##########")
        df = read_any(INPUTS[prefix])
        assert len(df) == EXPECTED_ROWS[prefix], (
            f"{prefix} rows {len(df):,} != expected {EXPECTED_ROWS[prefix]:,}")
        n_cols_in = df.shape[1]
        print(f"loaded Week 6 enriched: {len(df):,} rows x {n_cols_in} cols")
        preview(df, f"{prefix} input as loaded")

        df = iqr_flags(df, prefix)
        flag_cols = list(FLAG_OF.values()) + ["any_iqr_outlier_flag"]
        preview(df[df["any_iqr_outlier_flag"] == 1], f"{prefix} flagged examples",
                flag_cols)
        filtered = df[df["any_iqr_outlier_flag"] == 0].copy()
        preview(filtered, f"{prefix} filtered result", flag_cols)

        written_comparison(df, filtered, prefix)
        if prefix == "Sold":
            capstone_measurements(df)
        confirm_carry_through(df, prefix)

        # Nothing deleted from the flagged file; filtered = any-flag rows removed.
        assert len(df) == EXPECTED_ROWS[prefix]
        assert df.shape[1] == n_cols_in + 4
        assert len(filtered) == len(df) - int(df["any_iqr_outlier_flag"].sum())

        flagged_out = os.path.join(
            OUTPUT_DIR, f"Week 7 _ Deliverable _ {prefix} Residential IQR Flagged.csv")
        filtered_out = os.path.join(
            OUTPUT_DIR, f"Week 7 _ Deliverable _ {prefix} Residential IQR Filtered.csv")
        df.to_csv(flagged_out, index=False)
        filtered.to_csv(filtered_out, index=False)
        print(f"\nsaved flagged  -> {os.path.basename(flagged_out)} "
              f"({len(df):,} rows x {df.shape[1]} cols -- nothing deleted)")
        print(f"saved filtered -> {os.path.basename(filtered_out)} "
              f"({len(filtered):,} rows)")
        print("PROVENANCE: the FILTERED file is for general market-trend charts "
              "ONLY. All investor/flip/agent/sentinel capstone metrics use the "
              "FLAGGED (pre-IQR) file -- locked council ruling.")


if __name__ == "__main__":
    main()


# =============================================================================
# RUN LOG (observed)
# -----------------------------------------------------------------------------
# SOLD: fences ClosePrice <= $2,342,150 | LivingArea <= 3,680.5 | DOM <= 110.5
#   (all upper-only, as expected on right-skewed data). Flagged: price 33,731
#   (7.41%) | size 19,862 (4.36%) | DOM 33,960 (7.46%) | any 70,446 (15.47%).
#   Filtered: 385,003 rows (84.53% retained). Comparison: median ClosePrice
#   $815,000 -> $780,000 (-4.3%) while MEAN collapses $1,123,321 -> $887,946
#   (-21%): the filter mostly removes the luxury/slow tails; medians barely move.
# LISTING: fences $2,373,500 / 3,743 / 105.5. any 76,694 (15.21%);
#   filtered 427,468 (84.79% retained); median $820,000 -> $787,500.
#   Null-ClosePrice listings (16.4%) pass the price fence vacuously and stay.
# FILTER-SKEW (capstone measurements): county any-flag rates are FLAT
#   (Riverside 15.4% vs LA 16.4% / Orange 16.9% / SD 12.6%) -- the filtered file
#   does not skew the report geography. Sub-$600K investor-tier stock: only the
#   DOM fence fires (10.8%); price fence 0 by construction. DOM tail composition:
#   40.1% sub-$600K, 21.4% Riverside, 4.8% NONMEMBER-buyer -- the DOM fence DOES
#   remove investor-tier stale inventory, confirming the pre-IQR rule for all
#   capstone metrics.
# District + engineered columns carried through all 4 outputs (asserted+printed).
# Sanity band 12-20%: PASSED at 15.47% / 15.21%.
# =============================================================================

# =============================================================================
# OBSERVED OUTPUT -- verbatim from the run (all printed tables + previews)
# -----------------------------------------------------------------------------
# 
# ########## SOLD ##########
# loaded Week 6 enriched: 455,449 rows x 62 cols
# 
# -- preview: Sold input as loaded (first 5 rows) --
#  ClosePrice  LivingArea  DaysOnMarket    YrMo  CountyOrParish
#   5000000.0      4354.0             0 2024-01    Contra Costa
#    858000.0      1995.0             0 2024-01       Riverside
#   1890500.0      3194.0             0 2024-01     Los Angeles
#   2100000.0      3736.0             0 2024-01 San Luis Obispo
#   2340000.0      2442.0             0 2024-01     Santa Clara
# 
# === IQR FENCES & PERCENTILES (Sold) ===
# 
# ClosePrice: n=455,447 (non-null)  min=525  max=110,000,000
#   p1=201,609  p5=339,000  p25=571,900  p50=815,000  p75=1,280,000  p95=2,800,000  p99=5,450,000
#   Q1=571,900  Q3=1,280,000  IQR=708,100  fences=[-490,250.0, 2,342,150.0]
#   flagged: below=0  above=33,731  total=33,731 (7.41% of rows)
# 
# LivingArea: n=455,179 (non-null)  min=1  max=17,021,321
#   p1=608  p5=840  p25=1,248  p50=1,643  p75=2,221  p95=3,555  p99=5,265
#   Q1=1,248  Q3=2,221  IQR=973  fences=[-211.5, 3,680.5]
#   flagged: below=0  above=19,862  total=19,862 (4.36% of rows)
# 
# DaysOnMarket: n=455,449 (non-null)  min=0  max=12,430
#   p1=0  p5=1  p25=8  p50=19  p75=49  p95=133  p99=234
#   Q1=8  Q3=49  IQR=41  fences=[-53.5, 110.5]
#   flagged: below=0  above=33,960  total=33,960 (7.46% of rows)
# 
# any_iqr_outlier_flag: 70,446 rows (15.47%)
# 
# -- preview: Sold flagged examples (first 5 rows) --
#  ClosePrice  LivingArea  DaysOnMarket    YrMo  CountyOrParish  closeprice_iqr_outlier_flag  livingarea_iqr_outlier_flag  daysonmarket_iqr_outlier_flag  any_iqr_outlier_flag
#   5000000.0      4354.0             0 2024-01    Contra Costa                            1                            1                              0                     1
#   2100000.0      3736.0             0 2024-01 San Luis Obispo                            0                            1                              0                     1
#   1928800.0      3799.0             0 2024-01         Alameda                            0                            1                              0                     1
#   2460000.0      1936.0             0 2024-01     Santa Clara                            1                            0                              0                     1
#   9635000.0      5410.0            25 2024-01     Los Angeles                            1                            1                              0                     1
# 
# -- preview: Sold filtered result (first 5 rows) --
#  ClosePrice  LivingArea  DaysOnMarket    YrMo CountyOrParish  closeprice_iqr_outlier_flag  livingarea_iqr_outlier_flag  daysonmarket_iqr_outlier_flag  any_iqr_outlier_flag
#    858000.0      1995.0             0 2024-01      Riverside                            0                            0                              0                     0
#   1890500.0      3194.0             0 2024-01    Los Angeles                            0                            0                              0                     0
#   2340000.0      2442.0             0 2024-01    Santa Clara                            0                            0                              0                     0
#   1485000.0      1601.0             0 2024-01      San Diego                            0                            0                              0                     0
#   1130000.0      2136.0             1 2024-01    Los Angeles                            0                            0                              0                     0
# 
# === WRITTEN COMPARISON (Sold): before vs after IQR filtering ===
#                               rows  median_ClosePrice  mean_ClosePrice  median_LivingArea  median_DOM
# dataset                                                                                              
# before (flagged, all rows)  455449           815000.0        1123321.0             1643.0        19.0
# after (filtered)            385003           780000.0         887946.0             1570.0        16.0
# rows removed by filter: 70,446 (15.47%) | retained: 84.53%
# 
# === FILTER-SKEW MEASUREMENTS (sold) ===
# any-flag rate by county (top 6 by sales):
#   Los Angeles      16.4% flagged
#   Riverside        15.4% flagged
#   San Diego        12.6% flagged
#   Orange           16.9% flagged
#   San Bernardino   12.8% flagged
#   Alameda          10.7% flagged
# 
# sub-$600K (investor-tier) stock: 126,346 rows | any-flag 10.8% (price fence cannot fire here; drivers below)
#   ClosePrice   fence fired on 0 (0.0%)
#   LivingArea   fence fired on 117 (0.1%)
#   DaysOnMarket fence fired on 13,610 (10.8%)
# 
# DOM-fence tail (slow sales, 33,960 rows): 40.1% sub-$600K | 21.4% Riverside | 4.8% NONMEMBER-buyer
# 
# district_match_status carry-through (Sold):
# district_match_status
# matched                307683
# no_unified_district     94032
# missing_coords          53625
# invalid_coords            109
# 
# saved flagged  -> Week 7 _ Deliverable _ Sold Residential IQR Flagged.csv (455,449 rows x 66 cols -- nothing deleted)
# saved filtered -> Week 7 _ Deliverable _ Sold Residential IQR Filtered.csv (385,003 rows)
# PROVENANCE: the FILTERED file is for general market-trend charts ONLY. All investor/flip/agent/sentinel capstone metrics use the FLAGGED (pre-IQR) file -- locked council ruling.
# 
# ########## LISTING ##########
# loaded Week 6 enriched: 504,162 rows x 60 cols
# 
# -- preview: Listing input as loaded (first 5 rows) --
#  ClosePrice  LivingArea  DaysOnMarket    YrMo CountyOrParish
#         NaN      2338.0            36     NaN      Riverside
#    320000.0      1212.0             0 2026-05      Riverside
#    160000.0      1008.0            10 2026-04           Lake
#   2000000.0      2573.0            98 2026-04    Los Angeles
#   3200000.0      1381.0             0 2025-05      San Diego
# 
# === IQR FENCES & PERCENTILES (Listing) ===
# 
# ClosePrice: n=421,386 (non-null)  min=525  max=110,000,000
#   p1=206,021  p5=340,000  p25=576,000  p50=820,000  p75=1,295,000  p95=2,800,000  p99=5,372,640
#   Q1=576,000  Q3=1,295,000  IQR=719,000  fences=[-502,500.0, 2,373,500.0]
#   flagged: below=0  above=30,449  total=30,449 (6.04% of rows)
# 
# LivingArea: n=503,813 (non-null)  min=1  max=17,021,321
#   p1=601  p5=834  p25=1,248  p50=1,650  p75=2,246  p95=3,649  p99=5,596
#   Q1=1,248  Q3=2,246  IQR=998  fences=[-249.0, 3,743.0]
#   flagged: below=0  above=22,901  total=22,901 (4.54% of rows)
# 
# DaysOnMarket: n=504,162 (non-null)  min=0  max=12,430
#   p1=0  p5=1  p25=8  p50=18  p75=47  p95=130  p99=239
#   Q1=8  Q3=47  IQR=39  fences=[-50.5, 105.5]
#   flagged: below=0  above=38,811  total=38,811 (7.70% of rows)
# 
# any_iqr_outlier_flag: 76,694 rows (15.21%)
# 
# -- preview: Listing flagged examples (first 5 rows) --
#  ClosePrice  LivingArea  DaysOnMarket    YrMo CountyOrParish  closeprice_iqr_outlier_flag  livingarea_iqr_outlier_flag  daysonmarket_iqr_outlier_flag  any_iqr_outlier_flag
#   3200000.0      1381.0             0 2025-05      San Diego                            1                            0                              0                     1
#    299999.0      1310.0           159 2025-10      San Diego                            0                            0                              1                     1
#   4924000.0      3413.0             0 2025-02         Orange                            1                            0                              0                     1
#  10000000.0      5440.0             0 2025-01         Orange                            1                            1                              0                     1
#   5200000.0      3743.0             0 2025-04      Riverside                            1                            0                              0                     1
# 
# -- preview: Listing filtered result (first 5 rows) --
#  ClosePrice  LivingArea  DaysOnMarket    YrMo CountyOrParish  closeprice_iqr_outlier_flag  livingarea_iqr_outlier_flag  daysonmarket_iqr_outlier_flag  any_iqr_outlier_flag
#         NaN      2338.0            36     NaN      Riverside                            0                            0                              0                     0
#    320000.0      1212.0             0 2026-05      Riverside                            0                            0                              0                     0
#    160000.0      1008.0            10 2026-04           Lake                            0                            0                              0                     0
#   2000000.0      2573.0            98 2026-04    Los Angeles                            0                            0                              0                     0
#   1780000.0      3200.0            46 2025-06      San Diego                            0                            0                              0                     0
# 
# === WRITTEN COMPARISON (Listing): before vs after IQR filtering ===
#                               rows  median_ClosePrice  mean_ClosePrice  median_LivingArea  median_DOM
# dataset                                                                                              
# before (flagged, all rows)  504162           820000.0        1127006.0             1650.0        18.0
# after (filtered)            427468           787500.0         898187.0             1580.0        16.0
# rows removed by filter: 76,694 (15.21%) | retained: 84.79%
# 
# district_match_status carry-through (Listing):
# district_match_status
# matched                348301
# no_unified_district    106190
# missing_coords          49455
# invalid_coords            216
# 
# saved flagged  -> Week 7 _ Deliverable _ Listing Residential IQR Flagged.csv (504,162 rows x 64 cols -- nothing deleted)
# saved filtered -> Week 7 _ Deliverable _ Listing Residential IQR Filtered.csv (427,468 rows)
# PROVENANCE: the FILTERED file is for general market-trend charts ONLY. All investor/flip/agent/sentinel capstone metrics use the FLAGGED (pre-IQR) file -- locked council ruling.
# =============================================================================
