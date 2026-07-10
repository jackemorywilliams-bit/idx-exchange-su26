"""
Weeks 2-3 Deliverable (Part 2 of 2) - Mortgage Rate Enrichment.

Enrich BOTH datasets (sold + listings) with the national 30-year fixed mortgage rate
from FRED (series MORTGAGE30US), joined on a monthly key.

  1. Fetch MORTGAGE30US from FRED (timeout + retry, with a local cache fallback).
  2. Resample the weekly rates to monthly averages (year_month).
  3. Build the reduced, Residential, 30-month (Jan 2024 - June 2026) sold + listings
     datasets via common.load_residential_reduced (same keep-list + file discovery as
     the structuring script -- single source of truth).
  4. Build a matching year_month key (sold <- CloseDate, listings <- ListingContractDate)
     and left-merge the monthly rate onto both.
  5. Validate: confirm NO null rate values remain (unmatched months are reported).
  6. Save both enriched datasets as new CSVs.

Continuity anchors (30 months): sold Residential 455,658 | listings Residential 504,466.
"""

import io
import os
import time

import pandas as pd
import requests

import common

# --- Configuration -----------------------------------------------------------
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"

OUTPUT_DIR = os.path.expanduser(os.environ.get("CRMLS_OUTPUT_DIR", "."))
SOLD_OUT = os.path.join(OUTPUT_DIR, "sold_with_rates.csv")
LISTINGS_OUT = os.path.join(OUTPUT_DIR, "listings_with_rates.csv")
FRED_CACHE = os.path.join(OUTPUT_DIR, "fred_mortgage30us_cache.csv")

EXPECTED_RESIDENTIAL = {"Sold": 455_658, "Listing": 504_466}


def fetch_fred(retries=4, backoff=2.0):
    """Fetch MORTGAGE30US with retry + exponential backoff; cache on success."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(FRED_URL, timeout=30)
            resp.raise_for_status()
            with open(FRED_CACHE, "w") as fh:
                fh.write(resp.text)
            print(f"fetched MORTGAGE30US from FRED ({len(resp.text):,} bytes); "
                  f"cached -> {FRED_CACHE}")
            return pd.read_csv(io.StringIO(resp.text), parse_dates=["observation_date"])
        except (requests.RequestException, ValueError) as exc:
            wait = backoff ** attempt
            print(f"  FRED fetch attempt {attempt}/{retries} failed ({exc}); "
                  f"retrying in {wait:.0f}s")
            time.sleep(wait)
    if os.path.exists(FRED_CACHE):
        print(f"network unavailable -- falling back to cache: {FRED_CACHE}")
        return pd.read_csv(FRED_CACHE, parse_dates=["observation_date"])
    raise SystemExit("Could not fetch MORTGAGE30US from FRED and no cache exists.")


def monthly_rates():
    mortgage = fetch_fred()
    mortgage.columns = ["date", "rate_30yr_fixed"]
    print("\nFRED weekly rates (head):")
    print(mortgage.head().to_string(index=False))

    mortgage["year_month"] = mortgage["date"].dt.to_period("M")
    monthly = (mortgage.groupby("year_month")["rate_30yr_fixed"]
                       .mean().round(4).reset_index())
    print(f"\nresampled weekly -> monthly: {len(monthly)} months "
          f"({monthly['year_month'].min()} .. {monthly['year_month'].max()})")
    print("monthly resampled rates (head):")
    print(monthly.head().to_string(index=False))
    return monthly


def enrich(prefix, date_col, monthly, out_path):
    """Load reduced Residential data, build year_month key, merge rate, validate, save."""
    print(f"\n=== {prefix.upper()} (keyed off {date_col}) ===")
    df = common.load_residential_reduced(prefix)
    assert len(df) == EXPECTED_RESIDENTIAL[prefix], (
        f"{prefix} Residential rows {len(df):,} != baseline "
        f"{EXPECTED_RESIDENTIAL[prefix]:,}")
    df["year_month"] = pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M")

    merged = df.merge(monthly, on="year_month", how="left")
    n_null = int(merged["rate_30yr_fixed"].isnull().sum())
    print(f"rows: {len(merged):,} x {merged.shape[1]} cols | null rate after merge: {n_null:,}")
    if n_null:
        unmatched = (merged.loc[merged["rate_30yr_fixed"].isnull(), "year_month"]
                     .value_counts().head(10))
        print(f"  WARNING: {n_null:,} rows lack a rate. Top unmatched year_months:")
        print(unmatched.to_string())
    else:
        print("  VALIDATION OK: every row matched a monthly rate (0 nulls).")

    merged.to_csv(out_path, index=False)
    print(f"saved -> {out_path}")
    cols = [date_col, "year_month", "ClosePrice", "rate_30yr_fixed"]
    print("preview:")
    print(merged[[c for c in cols if c in merged.columns]].head().to_string(index=False))
    return n_null


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    monthly = monthly_rates()

    null_sold = enrich("Sold", "CloseDate", monthly, SOLD_OUT)
    null_list = enrich("Listing", "ListingContractDate", monthly, LISTINGS_OUT)

    print("\n=== MERGE VALIDATION SUMMARY ===")
    print(f"sold null rates:     {null_sold:,}")
    print(f"listings null rates: {null_list:,}")
    if null_sold or null_list:
        raise SystemExit("Merge validation FAILED: null rate values remain.")
    print("ALL CLEAR: both enriched datasets have zero null rate values.")


if __name__ == "__main__":
    main()


# =============================================================================
# RUN LOG (observed) - 30 months (Jan 2024 - June 2026)
# -----------------------------------------------------------------------------
# FRED MORTGAGE30US fetched live; weekly 1971-04 .. 2026-07; resampled to 664 months.
# SOLD     (keyed off CloseDate):          455,658 rows x 33 cols | null rate 0  OK
# LISTINGS (keyed off ListingContractDate): 504,466 rows x 31 cols | null rate 0  OK
#   (listings lack ListAgentAOR/BuyerAgentAOR in the source extract, so 29 kept +
#    year_month + rate = 31 cols; sold keeps 31 + 2 = 33.)
# Both enriched datasets have ZERO null rate values.
# =============================================================================
