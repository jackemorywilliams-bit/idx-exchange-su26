"""
Shared helpers for the Weeks 2-3 pipeline (used by both scripts).

Single source of truth for:
  - monthly-file discovery (dedup by YYYYMM across two data folders; no double-count),
  - the encoding-safe CSV reader,
  - the dashboard KEEP_COLUMNS list (the column-drop decision), and
  - loading a Residential, column-reduced dataset.

The column keep-list was set by a 4-specialist council (BI/dashboard, data quality,
real-estate domain, data engineering) against the two final deliverables -- a MARKET
ANALYSIS dashboard and a COMPETITIVE ANALYSIS dashboard -- per the handbook rule:
drop any column >90% null, and keep only fields that feed those dashboards.
"""

import glob
import os
import re

import pandas as pd

# Folders that may hold monthly CRMLS files. The dated subfolder is the canonical
# historical store; top-level data/ holds newly-arrived months (and stale duplicates
# of a few months -- which is why we dedup by YYYYMM and let the subfolder win).
SEARCH_DIRS = [
    os.path.expanduser(os.environ.get(
        "CRMLS_DATA_DIR",
        "~/idx-exchange/data/Listing & Sold (Jan 2024 - May 2026)")),
    os.path.expanduser("~/idx-exchange/data"),
]

# Expected contiguous month range on disk: 2024-01 .. 2026-06 (30 months).
EXPECTED_MONTHS = [f"{y}{m:02d}" for y in (2024, 2025, 2026)
                   for m in range(1, 13) if not (y == 2026 and m > 6)]

# --- The column-drop decision: 31 columns kept for the two dashboards ----------
KEEP_COLUMNS = [
    # id / join key
    "ListingKey",
    # price
    "ClosePrice", "ListPrice", "OriginalListPrice",
    # dates + time-on-market (CloseDate & ListingContractDate are also the rate join keys)
    "CloseDate", "ListingContractDate", "PurchaseContractDate", "DaysOnMarket",
    # status + product mix
    "MlsStatus", "PropertyType", "PropertySubType",
    # size / attributes
    "LivingArea", "LotSizeSquareFeet", "BedroomsTotal", "BathroomsTotalInteger",
    "YearBuilt",
    # geography
    "CountyOrParish", "City", "PostalCode", "StateOrProvince", "MLSAreaMajor",
    "Latitude", "Longitude",
    # competitive: offices
    "ListOfficeName", "BuyerOfficeName",
    # competitive: agents
    "ListAgentFullName", "ListAgentAOR",
    "BuyerAgentFirstName", "BuyerAgentLastName", "BuyerAgentMlsId", "BuyerAgentAOR",
]

# Date columns used to join the FRED monthly mortgage rate -- must survive the drop.
JOIN_KEYS = {"Sold": "CloseDate", "Listing": "ListingContractDate"}


def read_any(path):
    """Read a CSV as UTF-8, falling back to Windows-1252 for the FileZilla files."""
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="cp1252")


def discover_monthly(prefix):
    """Return sorted [(yyyymm, path)] for CRMLS<prefix><YYYYMM>.csv.

    Dedups by YYYYMM across SEARCH_DIRS (first dir wins, so the canonical subfolder
    beats stale top-level duplicates). Asserts exactly the 30 expected contiguous
    months so a missing or double-counted file fails loudly instead of silently.
    """
    pat = re.compile(rf"CRMLS{prefix}(\d{{6}})\.csv$")
    found = {}
    for d in SEARCH_DIRS:
        for path in sorted(glob.glob(os.path.join(d, f"CRMLS{prefix}*.csv"))):
            m = pat.search(os.path.basename(path))
            if m:
                found.setdefault(m.group(1), path)  # first dir wins
    months = sorted(found)
    if months != EXPECTED_MONTHS:
        missing = sorted(set(EXPECTED_MONTHS) - set(months))
        extra = sorted(set(months) - set(EXPECTED_MONTHS))
        raise SystemExit(
            f"{prefix}: month set mismatch. found {len(months)} "
            f"(expected {len(EXPECTED_MONTHS)}). missing={missing} extra={extra}")
    return [(mm, found[mm]) for mm in months]


def load_unfiltered(prefix):
    """Concatenate every monthly file for `prefix` (un-filtered). Asserts lossless."""
    files = discover_monthly(prefix)
    frames, rows_sum = [], 0
    for _, path in files:
        df = read_any(path)
        rows_sum += len(df)
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    assert len(combined) == rows_sum, "Concatenation not lossless!"
    return combined, len(files), rows_sum


def apply_keep(df):
    """Reduce to KEEP_COLUMNS (those present), preserving KEEP order."""
    return df[[c for c in KEEP_COLUMNS if c in df.columns]].copy()


def load_residential_reduced(prefix):
    """Concat -> filter Residential -> reduce to the dashboard keep-list."""
    combined, _, _ = load_unfiltered(prefix)
    residential = combined[combined["PropertyType"] == "Residential"]
    reduced = apply_keep(residential)
    key = JOIN_KEYS[prefix]
    assert key in reduced.columns, f"join key {key} was dropped -- keep-list bug!"
    return reduced
