"""
Week 1 Deliverable - Concatenate monthly CRMLS files into combined datasets.

Reads every monthly file from January 2024 through the most recently completed
calendar month (CRMLSListing<YYYYMM>.csv and CRMLSSold<YYYYMM>.csv), concatenates
each group into one combined dataset, filters BOTH to PropertyType == 'Residential'
only, and writes the two results as new CSVs.

Row counts are printed at four checkpoints for each dataset so the operation can be
audited: (1) sum of rows across the individual monthly files, (2) rows after
concatenation, (3) rows before the Residential filter, (4) rows after the filter.
The observed counts from the actual run are recorded in the RUN LOG at the bottom.

Note: the historical (FileZilla) files are Windows-1252 encoded while the
extraction-script files are UTF-8, so each file is read with a utf-8 -> cp1252
fallback. The combined outputs are written as UTF-8.
"""

import glob
import os

import pandas as pd

# --- Configuration -----------------------------------------------------------
# Folder holding the per-month files (Jan 2024 through the latest completed month),
# named CRMLSListing<YYYYMM>.csv / CRMLSSold<YYYYMM>.csv. Override the paths with env
# vars so this runs on any machine without editing the script. Data files are
# gitignored and kept local only.
DATA_DIR = os.path.expanduser(os.environ.get("CRMLS_DATA_DIR", "./data"))
OUTPUT_DIR = os.path.expanduser(os.environ.get("CRMLS_OUTPUT_DIR", "."))

# The two canonical datasets the whole project builds toward.
LISTINGS_OUT = os.path.join(OUTPUT_DIR, "listings.csv")
SOLD_OUT = os.path.join(OUTPUT_DIR, "sold.csv")


def read_any(path):
    """Read a CSV as UTF-8, falling back to Windows-1252 for the FileZilla files."""
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="cp1252")


def combine(prefix, out_path, label):
    # Match only the monthly files: CRMLS<prefix> + 6 digits (YYYYMM) + .csv.
    pattern = os.path.join(DATA_DIR, f"CRMLS{prefix}[0-9][0-9][0-9][0-9][0-9][0-9].csv")
    files = sorted(glob.glob(pattern))

    print(f"\n=== {label} ===")
    print(f"monthly files found: {len(files)} "
          f"({os.path.basename(files[0])} ... {os.path.basename(files[-1])})")

    # --- Row count BEFORE concatenation: sum of rows across the separate files.
    frames = []
    rows_before_concat = 0
    for f in files:
        df = read_any(f)
        rows_before_concat += len(df)
        frames.append(df)
    print(f"rows BEFORE concatenation (sum of monthly files): {rows_before_concat:,}")

    # --- Concatenate all months into a single dataset.
    combined = pd.concat(frames, ignore_index=True)
    print(f"rows AFTER concatenation:                         {len(combined):,}")

    # --- Row count BEFORE the Residential filter.
    print(f"rows BEFORE Residential filter:                   {len(combined):,}")

    # --- Filter to PropertyType == 'Residential' only.
    residential = combined[combined["PropertyType"] == "Residential"]
    print(f"rows AFTER Residential filter:                    {len(residential):,}")

    # --- Save the combined, filtered dataset as a new CSV (UTF-8).
    residential.to_csv(out_path, index=False)
    print(f"saved -> {out_path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    combine("Listing", LISTINGS_OUT, "LISTINGS")
    combine("Sold", SOLD_OUT, "SOLD")


if __name__ == "__main__":
    main()


# =============================================================================
# RUN LOG (observed counts) - run on the Jan 2024 - May 2026 set (29 months each)
# -----------------------------------------------------------------------------
# LISTINGS (29 files: CRMLSListing202401 ... CRMLSListing202605)
#   rows before concatenation (sum of monthly files): 729,251
#   rows after concatenation:                         729,251   (no rows lost)
#   rows before Residential filter:                   729,251
#   rows after Residential filter:                    480,383   (248,868 non-Residential removed)
#
# SOLD (29 files: CRMLSSold202401 ... CRMLSSold202605)
#   rows before concatenation (sum of monthly files): 655,362
#   rows after concatenation:                         655,362   (no rows lost)
#   rows before Residential filter:                   655,362
#   rows after Residential filter:                    438,115   (217,247 non-Residential removed)
# =============================================================================
