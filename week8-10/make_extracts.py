"""
Weeks 8-10 - Build the Tableau .hyper extracts for the dashboard workbooks.

Reads the Week 7 IQR FLAGGED files (canonical base: every row present, 0/1 flags
carried) and writes two trimmed extracts into ~/idx-exchange/tableau/:

  market_sold.hyper      455,449 rows -- close date/month, price, ratio, DOM,
                         geography, subtype, district, IQR flag, mortgage rate
  market_listings.hyper  504,162 rows -- listing date/month, geography, subtype,
                         IQR flag

Column trimming is deliberate: only fields the market_analysis views and their
required filters (City / CountyOrParish / PostalCode / PropertySubType) need.
Each sheet applies its own outlier policy via any_iqr_outlier_flag (locked rule:
IQR-filtered base for distortion-prone averages; all rows for counts/medians).
Extracts are LOCAL ONLY until the confidentiality confirmation arrives.
"""

import os

import pandas as pd
from tableauhyperapi import (Connection, CreateMode, HyperProcess, Inserter,
                             SqlType, TableDefinition, TableName, Telemetry)

DELIV = os.path.expanduser(os.environ.get("CRMLS_DELIV_DIR", "~/idx-exchange/deliverables"))
OUT_DIR = os.path.expanduser("~/idx-exchange/tableau")

SOLD_IN = os.path.join(DELIV, "Week 7 _ Deliverable _ Sold Residential IQR Flagged.csv")
LIST_IN = os.path.join(DELIV, "Week 7 _ Deliverable _ Listing Residential IQR Flagged.csv")
EXPECTED = {"sold": 455_449, "listings": 504_162}

SOLD_COLS = {
    "CloseDate": SqlType.date(), "YrMo": SqlType.text(),
    "ClosePrice": SqlType.double(), "price_ratio": SqlType.double(),
    "days_on_market": SqlType.double(), "City": SqlType.text(),
    "CountyOrParish": SqlType.text(), "PostalCode": SqlType.text(),
    "PropertySubType": SqlType.text(), "DistrictName": SqlType.text(),
    "any_iqr_outlier_flag": SqlType.big_int(), "rate_30yr_fixed": SqlType.double(),
}
LIST_COLS = {
    "ListingContractDate": SqlType.date(), "ListYrMo": SqlType.text(),
    "City": SqlType.text(), "CountyOrParish": SqlType.text(),
    "PostalCode": SqlType.text(), "PropertySubType": SqlType.text(),
    "any_iqr_outlier_flag": SqlType.big_int(),
}


def build(hyper, name, df, cols):
    table = TableDefinition(TableName("Extract", "Extract"),
                            [TableDefinition.Column(c, t) for c, t in cols.items()])
    path = os.path.join(OUT_DIR, name)
    with Connection(hyper.endpoint, path, CreateMode.CREATE_AND_REPLACE) as conn:
        conn.catalog.create_schema("Extract")
        conn.catalog.create_table(table)
        rows = list(df[list(cols)].itertuples(index=False, name=None))
        rows = [tuple(None if pd.isna(v) else v for v in r) for r in rows]
        with Inserter(conn, table) as ins:
            ins.add_rows(rows)
            ins.execute()
        n = conn.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."Extract"')
    print(f"built {name}: {n:,} rows x {len(cols)} cols")
    return n


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    sold = pd.read_csv(SOLD_IN, usecols=list(SOLD_COLS), low_memory=False)
    assert len(sold) == EXPECTED["sold"], f"sold rows {len(sold):,}"
    sold["CloseDate"] = pd.to_datetime(sold["CloseDate"], errors="coerce").dt.date
    sold["PostalCode"] = sold["PostalCode"].astype(str).str.split(".").str[0]

    lst = pd.read_csv(LIST_IN, usecols=[c for c in LIST_COLS if c != "ListYrMo"],
                      low_memory=False)
    assert len(lst) == EXPECTED["listings"], f"listing rows {len(lst):,}"
    lst["ListingContractDate"] = pd.to_datetime(lst["ListingContractDate"],
                                                errors="coerce")
    # New-listings view is keyed off the LISTING month (YrMo upstream is close-month).
    lst["ListYrMo"] = lst["ListingContractDate"].dt.strftime("%Y-%m")
    lst["ListingContractDate"] = lst["ListingContractDate"].dt.date
    lst["PostalCode"] = lst["PostalCode"].astype(str).str.split(".").str[0]

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        n1 = build(hp, "market_sold.hyper", sold, SOLD_COLS)
        n2 = build(hp, "market_listings.hyper", lst, LIST_COLS)
    assert (n1, n2) == (EXPECTED["sold"], EXPECTED["listings"])
    print("extracts verified against Week 7 row anchors.")


if __name__ == "__main__":
    main()


# RUN LOG (observed)
# -----------------------------------------------------------------------------
# built market_sold.hyper: 455,449 rows x 12 cols
# built market_listings.hyper: 504,162 rows x 7 cols
# extracts verified against Week 7 row anchors. Dates land as real DATE types;
# PostalCode as text (leading-zero-safe); ListYrMo derived from listing date
# (upstream YrMo is close-month and would misdate the New Listings view).
# =============================================================================
