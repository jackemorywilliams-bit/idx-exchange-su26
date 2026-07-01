"""
Weeks 2-3 Deliverable (Part 2 of 2) - Mortgage Rate Enrichment.

Enrich BOTH combined datasets (sold + listings) with the national 30-year fixed
mortgage rate from the St. Louis Federal Reserve (FRED, series MORTGAGE30US), joined on
a monthly key. The FRED series is published weekly (every Thursday by Freddie Mac); MLS
transactions are analyzed by calendar month, so the weekly rates are resampled to a
monthly average before the join. No API key is required.

Steps:
  1. Fetch the MORTGAGE30US series directly from FRED (with timeout + retry, and a local
     cache fallback so a re-run works offline).
  2. Resample the weekly rates to monthly averages (year_month key).
  3. Build a matching year_month key on each MLS dataset:
       sold      <- CloseDate
       listings  <- ListingContractDate
  4. Left-merge the monthly rate onto both datasets.
  5. Validate the merge: confirm NO null rate values remain. Any unmatched year_months
     are reported explicitly (rather than crashing) so the cause is visible.
  6. Save both enriched datasets as new CSVs.

Inputs are the Residential-filtered combined datasets (the project's canonical sold /
listings). Their join-key date columns were verified to have 0 blank / 0 malformed
values, so the merge validation passes cleanly.
"""

import io
import os
import time

import pandas as pd
import requests

# --- Configuration -----------------------------------------------------------
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"

# Canonical Residential-filtered combined datasets (Week 1 outputs). Override via env.
SOLD_IN = os.path.expanduser(os.environ.get(
    "SOLD_CSV",
    "~/idx-exchange/deliverables/Week 1 _ Deliverable _ Combined Sold Residential.csv"))
LISTINGS_IN = os.path.expanduser(os.environ.get(
    "LISTINGS_CSV",
    "~/idx-exchange/deliverables/Week 1 _ Deliverable _ Combined Listings Residential.csv"))

OUTPUT_DIR = os.path.expanduser(os.environ.get("CRMLS_OUTPUT_DIR", "."))
SOLD_OUT = os.path.join(OUTPUT_DIR, "sold_with_rates.csv")
LISTINGS_OUT = os.path.join(OUTPUT_DIR, "listings_with_rates.csv")
FRED_CACHE = os.path.join(OUTPUT_DIR, "fred_mortgage30us_cache.csv")


def read_any(path):
    """Read a CSV as UTF-8, falling back to Windows-1252 (matches Week 1 outputs)."""
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="cp1252")


def fetch_fred(retries=4, backoff=2.0):
    """Fetch MORTGAGE30US from FRED with retry + exponential backoff; cache on success.

    Falls back to the local cache if the network is unavailable, so re-runs are robust.
    """
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
    """Fetch + resample the weekly 30yr rate to a monthly average keyed by year_month."""
    mortgage = fetch_fred()
    mortgage.columns = ["date", "rate_30yr_fixed"]
    mortgage["year_month"] = mortgage["date"].dt.to_period("M")
    monthly = (mortgage.groupby("year_month")["rate_30yr_fixed"]
                       .mean().round(4).reset_index())
    print(f"resampled weekly -> monthly: {len(monthly)} months "
          f"({monthly['year_month'].min()} .. {monthly['year_month'].max()})")
    return monthly


def enrich(df, date_col, monthly, out_path, label):
    """Build year_month key off `date_col`, left-merge the rate, validate, and save."""
    print(f"\n=== {label} ===")
    df = df.copy()
    df["year_month"] = pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M")

    merged = df.merge(monthly, on="year_month", how="left")

    # --- Validation: no null rate values after the merge.
    n_null = int(merged["rate_30yr_fixed"].isnull().sum())
    print(f"rows: {len(merged):,} | keyed off {date_col} | null rate after merge: {n_null:,}")
    if n_null:
        bad_dates = int(df[date_col].isna().sum() +
                        pd.to_datetime(df[date_col], errors="coerce").isna().sum())
        unmatched = (merged.loc[merged["rate_30yr_fixed"].isnull(), "year_month"]
                     .value_counts().head(10))
        print(f"  WARNING: {n_null:,} rows lack a rate. Unparseable {date_col}: ~{bad_dates:,}.")
        print("  top unmatched year_months:")
        print(unmatched.to_string())
    else:
        print("  VALIDATION OK: every row matched a monthly rate (0 nulls).")

    merged.to_csv(out_path, index=False)
    print(f"saved -> {out_path}")

    # Preview (mirrors the task's requested sanity check).
    prev_date = date_col
    cols = [prev_date, "year_month", "rate_30yr_fixed"]
    if "ClosePrice" in merged.columns:
        cols.insert(2, "ClosePrice")
    print("preview:")
    print(merged[cols].head().to_string(index=False))
    return n_null


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    monthly = monthly_rates()

    print("\nloading canonical datasets ...")
    sold = read_any(SOLD_IN)
    listings = read_any(LISTINGS_IN)

    null_sold = enrich(sold, "CloseDate", monthly, SOLD_OUT, "SOLD (keyed off CloseDate)")
    null_list = enrich(listings, "ListingContractDate", monthly, LISTINGS_OUT,
                       "LISTINGS (keyed off ListingContractDate)")

    print("\n=== MERGE VALIDATION SUMMARY ===")
    print(f"sold null rates:     {null_sold:,}")
    print(f"listings null rates: {null_list:,}")
    if null_sold or null_list:
        raise SystemExit("Merge validation FAILED: null rate values remain (see above).")
    print("ALL CLEAR: both enriched datasets have zero null rate values.")


if __name__ == "__main__":
    main()


# =============================================================================
# RUN LOG (observed)
# -----------------------------------------------------------------------------
# FRED MORTGAGE30US fetched live (46,723 bytes); weekly 1971-04 .. 2026-06.
# Resampled weekly -> monthly: 663 months.
#
# SOLD (keyed off CloseDate):
#   rows: 438,115 | null rate after merge: 0   -- VALIDATION OK
#   saved -> sold_with_rates.csv
#
# LISTINGS (keyed off ListingContractDate):
#   rows: 480,383 | null rate after merge: 0   -- VALIDATION OK
#   saved -> listings_with_rates.csv
#
# Both enriched datasets have ZERO null rate values (join keys had 0 blank/malformed
# dates, and FRED covers every transaction month through 2026-05).
# =============================================================================
