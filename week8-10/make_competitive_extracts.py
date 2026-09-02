"""
Weeks 9-10 - Build the Tableau .hyper extracts for competitive_analysis.twb.

Reads the Week 7 FLAGGED sold file (canonical base: every closed sale present)
and writes three extracts into ~/idx-exchange/tableau/:

  competitive_sold.hyper   row-level: one row per closed sale with normalized
                           agent/office keys, sentinel flag, statewide office
                           ranks (units + volume) -- feeds the filterable office
                           views and the two zip-code heat maps
  top_agents.hyper         precomputed statewide top-100 listing agents by units
                           and by volume: rank, "Agent, Office", units, volume,
                           market share %
  brokerage_monthly.hyper  monthly listing sides / volume / share for the major
                           brokerage brands + Others (own-design "Brokerage
                           Power" dashboard)

Entity resolution (documented per the program's case-study convention):
  office_key = ListOfficeName upper-cased, trimmed, internal whitespace collapsed
  agent_key  = ListAgentFullName normalized the same way + " @ " + office_key
  Sentinel placeholders (NONMEMBER / NON-MEMBER / NONE / OUT OF AREA / UNKNOWN /
  blank) are flagged and EXCLUDED from every ranking and every share denominator.
Metric bases: units = count of closed sales (all rows, never outlier-filtered);
volume = sum of ClosePrice (all rows -- a real $20M sale is real volume).
"""

import os
import re

import pandas as pd
from tableauhyperapi import (Connection, CreateMode, HyperProcess, Inserter,
                             SqlType, TableDefinition, TableName, Telemetry)

DELIV = os.path.expanduser(os.environ.get("CRMLS_DELIV_DIR", "~/idx-exchange/deliverables"))
OUT_DIR = os.path.expanduser("~/idx-exchange/tableau")
SOLD_IN = os.path.join(DELIV, "Week 7 _ Deliverable _ Sold Residential IQR Flagged.csv")
EXPECTED_ROWS = 455_449

SENTINEL_PATTERNS = ("NONMEMBER", "NON-MEMBER", "NON MEMBER", "OUT OF AREA",
                     "UNKNOWN", "NOT A MEMBER", "NO AGENT", "NONE")

# Brokerage taxonomy: first matching rule wins (checked in this order).
BRANDS = [("Compass", "COMPASS"), ("Keller Williams", "KELLER WILLIAMS"),
          ("Coldwell Banker", "COLDWELL BANKER"), ("RE/MAX", "RE/MAX"),
          ("eXp Realty", "EXP REALTY"), ("Berkshire Hathaway", "BERKSHIRE"),
          ("Century 21", "CENTURY 21"), ("Sotheby's", "SOTHEBY"),
          ("Redfin", "REDFIN"), ("Real Broker", "REAL BROKER"),
          ("Equity Union", "EQUITY UNION"), ("Opendoor", "OPENDOOR")]


def norm(s):
    return re.sub(r"\s+", " ", str(s).strip()).upper() if pd.notna(s) else ""


def is_sentinel(key):
    if not key:
        return True
    return any(p in key for p in SENTINEL_PATTERNS)


def brokerage(key):
    for label, needle in BRANDS:
        if needle in key:
            return label
    return "Others"


def write_hyper(hyper, name, df, cols):
    table = TableDefinition(TableName("Extract", "Extract"),
                            [TableDefinition.Column(c, t) for c, t in cols.items()])
    path = os.path.join(OUT_DIR, name)
    with Connection(hyper.endpoint, path, CreateMode.CREATE_AND_REPLACE) as conn:
        conn.catalog.create_schema("Extract")
        conn.catalog.create_table(table)
        rows = [tuple(None if pd.isna(v) else v for v in r)
                for r in df[list(cols)].itertuples(index=False, name=None)]
        with Inserter(conn, table) as ins:
            ins.add_rows(rows)
            ins.execute()
        n = conn.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."Extract"')
    print(f"built {name}: {n:,} rows x {len(cols)} cols")
    return n


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    use = ["CloseDate", "YrMo", "ClosePrice", "City", "CountyOrParish", "PostalCode",
           "PropertySubType", "ListAgentFullName", "ListOfficeName", "Latitude", "Longitude"]
    df = pd.read_csv(SOLD_IN, usecols=use, low_memory=False)
    assert len(df) == EXPECTED_ROWS, f"sold rows {len(df):,}"
    df["CloseDate"] = pd.to_datetime(df["CloseDate"], errors="coerce").dt.date
    df["PostalCode"] = df["PostalCode"].astype(str).str.split(".").str[0]

    # ---- entity resolution -------------------------------------------------
    df["office_key"] = df["ListOfficeName"].map(norm)
    df["agent_name"] = df["ListAgentFullName"].map(norm)
    df["agent_key"] = df["agent_name"] + " @ " + df["office_key"]
    df["sentinel_flag"] = (df["office_key"].map(is_sentinel) | df["agent_name"].map(is_sentinel)).astype(int)
    df["brokerage"] = df["office_key"].map(brokerage)
    base = df[df.sentinel_flag == 0]
    print(f"sentinel rows excluded from rankings: {int(df.sentinel_flag.sum()):,} "
          f"({100 * df.sentinel_flag.mean():.2f}%) -> ranking base {len(base):,}")
    print("distinct offices (normalized):", base.office_key.nunique(),
          "| distinct agent keys:", base.agent_key.nunique())

    # ---- statewide office ranks (units + volume) ---------------------------
    off = base.groupby("office_key").agg(units=("YrMo", "size"), volume=("ClosePrice", "sum"))
    off["rank_units"] = off.units.rank(ascending=False, method="first").astype(int)
    off["rank_volume"] = off.volume.rank(ascending=False, method="first").astype(int)
    df["office_rank_units"] = df.office_key.map(off.rank_units).fillna(99999).astype(int)
    df["office_rank_volume"] = df.office_key.map(off.rank_volume).fillna(99999).astype(int)
    # One display name per normalized office: its most frequent raw spelling.
    raw = df["ListOfficeName"].fillna("").astype(str).str.strip()
    canonical = (pd.DataFrame({"k": df["office_key"], "raw": raw}).groupby("k")["raw"]
                 .agg(lambda x: x.value_counts().index[0]))
    df["office_display"] = df["office_key"].map(canonical)
    df["unit"] = 1  # SUM(unit) = units sold; reads as "Units Sold" in Measure Names
    # Zip codes ranked by closed sales (1 = most) so the zip heat maps can show the
    # busiest zips with a plain range filter.
    ca_zip = df.PostalCode.str.match(r"^9[0-6]\d{3}$", na=False)
    zr = df[ca_zip].groupby("PostalCode").size().rank(ascending=False, method="first").astype(int)
    df["zip_rank"] = df.PostalCode.map(zr).fillna(99999).astype(int)
    print(f"zips ranked (CA-format only): {int(ca_zip.sum()):,} rows; non-CA-format excluded from maps: {int((~ca_zip).sum()):,}")
    # Rank bands page the 100-row tables into 25-row views a fixed dashboard can show legibly.
    band = lambda r: ("01-25" if r <= 25 else "26-50" if r <= 50 else "51-75" if r <= 75 else "76-100" if r <= 100 else "100+")
    df["office_band_units"] = df.office_rank_units.map(band)
    df["office_band_volume"] = df.office_rank_volume.map(band)
    # Map coordinates offset to California's south-west corner (lat 32.3, lon -124.6) so a
    # zero-based axis starts exactly where the state starts; out-of-state/null -> null.
    in_ca = df.Latitude.between(32.3, 42.2) & df.Longitude.between(-124.6, -114.0)
    df["lat_ca"] = (df.Latitude - 32.3).where(in_ca)
    df["lon_ca"] = (df.Longitude + 124.6).where(in_ca)
    print(f"rows with California coordinates: {int(in_ca.sum()):,} ({100*in_ca.mean():.1f}%)")

    # ---- top-100 agents table ----------------------------------------------
    ag = base.groupby(["agent_key"]).agg(units=("YrMo", "size"), volume=("ClosePrice", "sum"),
                                         agent=("ListAgentFullName", "first"),
                                         office=("ListOfficeName", "first")).reset_index()
    tot_units, tot_vol = len(base), base.ClosePrice.sum()
    ag["share_units_pct"] = 100 * ag.units / tot_units
    ag["share_volume_pct"] = 100 * ag.volume / tot_vol
    ag["rank_units"] = ag.units.rank(ascending=False, method="first").astype(int)
    ag["rank_volume"] = ag.volume.rank(ascending=False, method="first").astype(int)
    ag["display"] = ag.agent.astype(str).str.strip() + ", " + ag.office.astype(str).str.strip()
    top = ag[(ag.rank_units <= 100) | (ag.rank_volume <= 100)].copy()
    top["band_units"] = top.rank_units.map(band)
    top["band_volume"] = top.rank_volume.map(band)
    print(f"top-100 agents table: {len(top)} rows (union of both rankings); "
          f"#1 by units = {top.sort_values('rank_units').iloc[0].display} "
          f"({int(top.units.max())} units)")

    # ---- brokerage monthly share -------------------------------------------
    bm = base.groupby(["brokerage", "YrMo"]).agg(sides=("YrMo", "size"), volume=("ClosePrice", "sum")).reset_index()
    month_tot = base.groupby("YrMo").size()
    bm["share_pct"] = 100 * bm.sides / bm.YrMo.map(month_tot)
    bm["month"] = pd.to_datetime(bm.YrMo + "-01").dt.date
    print("brokerage rows:", len(bm), "| brands:", bm.brokerage.nunique())

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        n1 = write_hyper(hp, "competitive_sold.hyper", df, {
            "CloseDate": SqlType.date(), "YrMo": SqlType.text(), "ClosePrice": SqlType.double(),
            "City": SqlType.text(), "CountyOrParish": SqlType.text(), "PostalCode": SqlType.text(),
            "PropertySubType": SqlType.text(), "office_display": SqlType.text(), "unit": SqlType.big_int(),
            "office_key": SqlType.text(), "brokerage": SqlType.text(),
            "sentinel_flag": SqlType.big_int(), "zip_rank": SqlType.big_int(), "office_rank_units": SqlType.big_int(),
            "office_band_units": SqlType.text(), "office_band_volume": SqlType.text(),
            "Latitude": SqlType.double(), "Longitude": SqlType.double(),
            "lat_ca": SqlType.double(), "lon_ca": SqlType.double(),
            "office_rank_volume": SqlType.big_int()})
        n2 = write_hyper(hp, "top_agents.hyper", top, {
            "display": SqlType.text(), "units": SqlType.big_int(), "volume": SqlType.double(),
            "share_units_pct": SqlType.double(), "share_volume_pct": SqlType.double(),
            "rank_units": SqlType.big_int(), "rank_volume": SqlType.big_int(),
            "band_units": SqlType.text(), "band_volume": SqlType.text()})
        n3 = write_hyper(hp, "brokerage_monthly.hyper", bm, {
            "brokerage": SqlType.text(), "month": SqlType.date(), "YrMo": SqlType.text(),
            "sides": SqlType.big_int(), "volume": SqlType.double(), "share_pct": SqlType.double()})
    assert n1 == EXPECTED_ROWS
    print("competitive extracts verified.")


if __name__ == "__main__":
    main()
