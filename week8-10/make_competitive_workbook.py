"""
Weeks 9-10 - Generate competitive_analysis.twb (code-authored workbook).

Handbook requirements (competitive_analysis.twbx), each its own tab:
  Top 100 listing agents by units / by volume          (statewide, precomputed)
  Top 100 listing offices by units / by volume         (filterable by County,
                                                        City, Zip, Property Type)
  Zip-code heat map of median close price              (filterable by month +
  Zip-code heat map of homes sold                       the four dimensions)
  + one competitive dashboard of our own design: "Brokerage Power" -- monthly
    listing-side share for the major brokerage brands, Opendoor's exit, KPIs.

Same standard as the market workbook: Fixed 1000x800, KPIs top-left, linked
filters (filter-group), direct labels, rounded formats, worksheets hidden.
Tables mirror the director's reference columns: Agent, Office | Units Sold |
Sales Volume | Market Share % | Rank. Sentinel placeholder records are excluded
from every ranking and denominator (see make_competitive_extracts.py).
"""

import argparse
import os

TABLEAU_DIR = os.path.expanduser("~/idx-exchange/tableau")
OUT = os.path.join(TABLEAU_DIR, "competitive_analysis.twb")
BUILD = "20262.26.0708.1337"

SOLD, AG, BM = "federated.csold", "federated.agents", "federated.brokerages"
CAP = {SOLD: "Competitive Sold (row-level)", AG: "Top Listing Agents (precomputed)",
       BM: "Brokerage Monthly Share (precomputed)"}

FMT_MONEY_M = "c&quot;$&quot;#,##0,,.00M;(&quot;$&quot;#,##0,,.00M)"
FMT_MONEY_B = "c&quot;$&quot;#,##0,,,.0B;(&quot;$&quot;#,##0,,,.0B)"
FMT_INT = "n#,##0;-#,##0"
FMT_PCT2 = "n#,##0.00&quot;%&quot;;-#,##0.00&quot;%&quot;"
FMT_PCT1 = "n#,##0.0&quot;%&quot;;-#,##0.0&quot;%&quot;"
FMT_MONEY_FULL = "c&quot;$&quot;#,##0;(&quot;$&quot;#,##0)"

SHARE_FORMULA = "SUM([unit]) / SUM({ EXCLUDE [office_display] : SUM([unit]) }) * 100"

SOLD_COLS = f"""
      <column caption='Close Date' datatype='date' name='[CloseDate]' role='dimension' type='ordinal' />
      <column caption='Month' datatype='string' name='[YrMo]' role='dimension' type='nominal' />
      <column caption='Sales Volume' datatype='real' default-format='{FMT_MONEY_FULL}' name='[ClosePrice]' role='measure' type='quantitative' />
      <column datatype='string' name='[City]' role='dimension' type='nominal' />
      <column caption='County' datatype='string' name='[CountyOrParish]' role='dimension' type='nominal' />
      <column caption='Zip Code' datatype='string' name='[PostalCode]' role='dimension' semantic-role='[ZipCode].[Name]' type='nominal' />
      <column caption='Property Type' datatype='string' name='[PropertySubType]' role='dimension' type='nominal' />
      <column caption='Listing Office' datatype='string' name='[office_display]' role='dimension' type='nominal' />
      <column caption='Units Sold' datatype='integer' default-format='{FMT_INT}' name='[unit]' role='measure' type='quantitative' />
      <column datatype='string' name='[office_key]' role='dimension' type='nominal' />
      <column caption='Brokerage' datatype='string' name='[brokerage]' role='dimension' type='nominal' />
      <column datatype='integer' name='[sentinel_flag]' role='dimension' type='ordinal' />
      <column datatype='integer' name='[zip_rank]' role='dimension' type='ordinal' />
      <column caption='Rank' datatype='integer' name='[office_rank_units]' role='dimension' type='ordinal' />
      <column caption='Rank' datatype='integer' name='[office_rank_volume]' role='dimension' type='ordinal' />
      <column caption='Page (by units)' datatype='string' name='[office_band_units]' role='dimension' type='nominal' />
      <column caption='Page (by volume)' datatype='string' name='[office_band_volume]' role='dimension' type='nominal' />
      <column caption='Latitude' datatype='real' name='[Latitude]' role='measure' type='quantitative' />
      <column caption='Longitude' datatype='real' name='[Longitude]' role='measure' type='quantitative' />
      <column caption='South to north' datatype='real' name='[lat_ca]' role='measure' type='quantitative' />
      <column caption='West to east' datatype='real' name='[lon_ca]' role='measure' type='quantitative' />
      <column caption='Market Share %' datatype='real' default-format='{FMT_PCT2}' name='[Calculation_share]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='{SHARE_FORMULA}' />
      </column>"""

AG_COLS = f"""
      <column caption='Listing Agent, Office' datatype='string' name='[display]' role='dimension' type='nominal' />
      <column caption='Units Sold' datatype='integer' default-format='{FMT_INT}' name='[units]' role='measure' type='quantitative' />
      <column caption='Sales Volume' datatype='real' default-format='{FMT_MONEY_FULL}' name='[volume]' role='measure' type='quantitative' />
      <column caption='Market Share % (units)' datatype='real' default-format='{FMT_PCT2}' name='[share_units_pct]' role='measure' type='quantitative' />
      <column caption='Market Share % (volume)' datatype='real' default-format='{FMT_PCT2}' name='[share_volume_pct]' role='measure' type='quantitative' />
      <column caption='Rank' datatype='integer' name='[rank_units]' role='dimension' type='ordinal' />
      <column caption='Rank' datatype='integer' name='[rank_volume]' role='dimension' type='ordinal' />
      <column caption='Page (by units)' datatype='string' name='[band_units]' role='dimension' type='nominal' />
      <column caption='Page (by volume)' datatype='string' name='[band_volume]' role='dimension' type='nominal' />"""

BM_COLS = f"""
      <column caption='Brokerage' datatype='string' name='[brokerage]' role='dimension' type='nominal' />
      <column caption='Month' datatype='date' name='[month]' role='dimension' type='ordinal' />
      <column datatype='string' name='[YrMo]' role='dimension' type='nominal' />
      <column caption='Listing Sides' datatype='integer' default-format='{FMT_INT}' name='[sides]' role='measure' type='quantitative' />
      <column caption='Sales Volume' datatype='real' default-format='{FMT_MONEY_B}' name='[volume]' role='measure' type='quantitative' />
      <column caption='Share of Listing Sides' datatype='real' default-format='{FMT_PCT1}' name='[share_pct]' role='measure' type='quantitative' />"""

GEO_DIMS = ["CountyOrParish", "City", "PostalCode", "PropertySubType"]
FG = {d: i + 1 for i, d in enumerate(GEO_DIMS)}
FG["YrMo"] = 5


def datasource(name, hyper, cols):
    cap = CAP[name]
    return f"""    <datasource caption='{cap}' inline='true' name='{name}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='{cap}' name='hyper.{name}'>
            <connection class='hyper' dbname='{TABLEAU_DIR}/{hyper}' schema='Extract' sslmode='' username='tableau_internal_user' />
          </named-connection>
        </named-connections>
        <relation connection='hyper.{name}' name='Extract' table='[Extract].[Extract]' type='table' />
      </connection>{cols}
      <extract count='-1' enabled='true' units='records'>
        <connection access_mode='readonly' class='hyper' dbname='{TABLEAU_DIR}/{hyper}' default-settings='yes' schema='Extract' sslmode='' tablename='Extract' username='tableau_internal_user'>
          <relation name='Extract' table='[Extract].[Extract]' type='table' />
        </connection>
      </extract>
    </datasource>"""


def inst(col, deriv, kind="qk"):
    tag = {"None": "none", "Sum": "sum", "Count": "cnt", "Median": "med", "Avg": "avg",
           "Min": "min", "User": "usr", "Month-Trunc": "tmn"}[deriv]
    typ = "quantitative" if kind == "qk" else ("ordinal" if kind == "ok" else "nominal")
    return (f"<column-instance column='[{col}]' derivation='{deriv}' name='[{tag}:{col}:{kind}]' "
            f"pivot='key' type='{typ}' />")


def geo_filters(ds, dims=GEO_DIMS, month=False):
    deps = "\n".join("            " + inst(d, "None", "nk") for d in dims)
    filts = "\n".join(
        f"          <filter class='categorical' column='[{ds}].[none:{d}:nk]' filter-group='{FG[d]}'>"
        f"<groupfilter function='level-members' level='[none:{d}:nk]' user:ui-enumeration='all' "
        f"user:ui-marker='enumerate' /></filter>" for d in dims)
    slices = "\n".join(f"            <column>[{ds}].[none:{d}:nk]</column>" for d in dims)
    if month:
        deps += "\n            " + inst("YrMo", "None", "nk")
        filts += (f"\n          <filter class='categorical' column='[{ds}].[none:YrMo:nk]' filter-group='{FG['YrMo']}'>"
                  f"<groupfilter function='level-members' level='[none:YrMo:nk]' user:ui-enumeration='all' "
                  f"user:ui-marker='enumerate' /></filter>")
        slices += f"\n            <column>[{ds}].[none:YrMo:nk]</column>"
    return deps, filts, slices


def sentinel_filter(ds):
    return (f"          <filter class='categorical' column='[{ds}].[none:sentinel_flag:ok]'>"
            f"<groupfilter function='member' level='[none:sentinel_flag:ok]' member='0' /></filter>")


def range_filter(ds, col, lo, hi):
    return (f"          <filter class='quantitative' column='[{ds}].[none:{col}:qk]' "
            f"included-values='in-range'><min>{lo}</min><max>{hi}</max></filter>")


def page_filter(ds, col, group):
    """Rank-band page filter, default page 01-25, linked to a dropdown card."""
    return (f"          <filter class='categorical' column='[{ds}].[none:{col}:nk]' filter-group='{group}'>"
            f"<groupfilter function='union' user:op='manual' user:ui-enumeration='inclusive' user:ui-marker='enumerate'>"
            f"<groupfilter function='member' level='[none:{col}:nk]' member='&quot;01-25&quot;' />"
            f"</groupfilter></filter>")


def measure_names_filter(ds, insts):
    members = "\n".join(f"              <groupfilter function='member' level='[:Measure Names]' "
                        f"member='&quot;[{ds}].{i}&quot;' />" for i in insts)
    return f"""          <filter class='categorical' column='[{ds}].[:Measure Names]'>
            <groupfilter function='union' user:op='manual'>
{members}
            </groupfilter>
          </filter>"""


TABLE_STYLE = """        <style>
          <style-rule element='cell'>
            <format attr='font-size' value='9' />
          </style-rule>
          <style-rule element='header'>
            <format attr='font-size' value='9' />
          </style-rule>
        </style>"""


def sheet(name, ds, title, deps, filters, slices, panes, rows, cols, extra_view="", style=TABLE_STYLE):
    return f"""    <worksheet name='{name}'>
      <layout-options>
        <title>
          <formatted-text><run>{title}</run></formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{CAP[ds]}' name='{ds}' />
          </datasources>
{extra_view}
          <datasource-dependencies datasource='{ds}'>
{deps}
          </datasource-dependencies>
{filters}
          <slices>
{slices}
          </slices>
          <aggregation value='true' />
        </view>
{style}
        <panes>
{panes}
        </panes>
        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>"""


def text_pane(ds, labels=False):
    return f"""          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Automatic' />
            <encodings>
              <text column='[{ds}].[Multiple Values]' />
            </encodings>
          </pane>"""


# ------------------------------------------------------------ ranked bar charts
BAR_LABELS = """            <style>
              <style-rule element='mark'>
                <format attr='mark-labels-show' value='true' />
                <format attr='mark-labels-cull' value='true' />
                <format attr='mark-labels-mode' value='all' />
              </style-rule>
            </style>"""


def bar_pane(ds, measure_inst):
    return f"""          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Bar' />
            <encodings>
              <text column='[{ds}].{measure_inst}' />
            </encodings>
{BAR_LABELS}
          </pane>"""


def agents_bars(name, by):
    """Top 100 listing agents as a ranked horizontal bar chart (statewide, precomputed)."""
    rank = f"rank_{by}"
    measure_col = "units" if by == "units" else "volume"
    measure_inst = f"[sum:{measure_col}:qk]"
    band = f"band_{by}"
    deps = "\n".join("            " + x for x in [
        inst("display", "None", "nk"), inst(rank, "None", "nk"), inst(rank, "None", "qk"),
        inst(band, "None", "nk"), inst(measure_col, "Sum")])
    filters = range_filter(AG, rank, 1, 100) + "\n" + page_filter(AG, band, 11 if by == "units" else 12)
    slices = f"            <column>[{AG}].[none:{rank}:qk]</column>\n            <column>[{AG}].[none:{band}:nk]</column>"
    title = f"Top 100 Listing Agents by {'Units Sold' if by == 'units' else 'Sales Volume'} -- 25 per page; use the Page dropdown for ranks 26-100"
    return sheet(name, AG, title, deps, filters, slices, bar_pane(AG, measure_inst),
                 f"([{AG}].[none:{rank}:nk] / [{AG}].[none:display:nk])", f"[{AG}].{measure_inst}", style="        <style />")


def offices_bars(name, by):
    """Top 100 listing offices as a ranked bar chart, filterable by the four dimensions."""
    rank_col = f"office_rank_{by}"
    measure_col = "unit" if by == "units" else "ClosePrice"
    measure_inst = f"[sum:{measure_col}:qk]"
    gdeps, gfilts, gslices = geo_filters(SOLD)
    band_col = f"office_band_{by}"
    deps = gdeps + "\n" + "\n".join("            " + x for x in [
        inst("office_display", "None", "nk"), inst("sentinel_flag", "None", "ok"),
        inst(rank_col, "None", "nk"), inst(rank_col, "None", "qk"), inst(band_col, "None", "nk"), inst(measure_col, "Sum")])
    filters = (gfilts + "\n" + sentinel_filter(SOLD) + "\n" + range_filter(SOLD, rank_col, 1, 100)
               + "\n" + page_filter(SOLD, band_col, 13 if by == "units" else 14))
    slices = (gslices + f"\n            <column>[{SOLD}].[none:sentinel_flag:ok]</column>"
              f"\n            <column>[{SOLD}].[none:{rank_col}:qk]</column>"
              f"\n            <column>[{SOLD}].[none:{band_col}:nk]</column>")
    title = f"Top 100 Listing Offices by {'Units Sold' if by == 'units' else 'Sales Volume'} -- 25 per page (Page dropdown); ranked statewide, filters show activity within your selection"
    return sheet(name, SOLD, title, deps, filters, slices, bar_pane(SOLD, measure_inst),
                 f"([{SOLD}].[none:{rank_col}:nk] / [{SOLD}].[none:office_display:nk])", f"[{SOLD}].{measure_inst}", style="        <style />")


# ---------------------------------------------------------------------- maps
def zip_map(name, title, color_inst, color_col, deriv):
    """Zip-code map: one circle per zip at its mean coordinates, colored by the
    measure and sized by homes sold. Built from the rows' own Latitude/Longitude."""
    gdeps, gfilts, gslices = geo_filters(SOLD, month=True)
    deps = gdeps + "\n" + "\n".join("            " + x for x in [
        inst("lat_ca", "None", "qk"), inst("lon_ca", "None", "qk"),
        inst("lat_ca", "Avg"), inst("lon_ca", "Avg"), inst("unit", "Sum"), inst(color_col, deriv)])
    gfilts = (gfilts + "\n" + range_filter(SOLD, "lat_ca", 0, 9.9)
              + "\n" + range_filter(SOLD, "lon_ca", 0, 10.6))
    gslices = (gslices + f"\n            <column>[{SOLD}].[none:lat_ca:qk]</column>"
               f"\n            <column>[{SOLD}].[none:lon_ca:qk]</column>")
    panes = f"""          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Circle' />
            <encodings>
              <color column='[{SOLD}].{color_inst}' />
              <size column='[{SOLD}].[sum:unit:qk]' />
              <lod column='[{SOLD}].[none:PostalCode:nk]' />
            </encodings>
            <style>
              <style-rule element='mark'>
                <format attr='mark-transparency' value='200' />
                <format attr='has-stroke' value='true' />
                <format attr='stroke-color' value='#ffffff' />
              </style-rule>
            </style>
          </pane>"""
    return sheet(name, SOLD, title, deps, gfilts, gslices, panes,
                 f"[{SOLD}].[avg:lat_ca:qk]", f"[{SOLD}].[avg:lon_ca:qk]", style="        <style />")


# ------------------------------------------------------------- brokerage power
LINE_END_LABELS = """            <style>
              <style-rule element='mark'>
                <format attr='mark-labels-show' value='true' />
                <format attr='mark-labels-mode' value='range' />
                <format attr='mark-labels-line-first' value='false' />
                <format attr='mark-labels-line-last' value='true' />
                <format attr='mark-labels-range-min' value='false' />
                <format attr='mark-labels-range-max' value='false' />
              </style-rule>
            </style>"""

BRANDS_SHOWN = ["Compass", "Coldwell Banker", "Keller Williams", "RE/MAX", "eXp Realty",
                "Real Broker", "Equity Union"]


def brand_filter(ds, brands):
    members = "\n".join(f"              <groupfilter function='member' level='[none:brokerage:nk]' "
                        f"member='&quot;{b}&quot;' />" for b in brands)
    return f"""          <filter class='categorical' column='[{ds}].[none:brokerage:nk]'>
            <groupfilter function='union' user:op='manual'>
{members}
            </groupfilter>
          </filter>"""


def month_filter(ds, months):
    members = "\n".join(f"              <groupfilter function='member' level='[none:YrMo:nk]' "
                        f"member='&quot;{m}&quot;' />" for m in months)
    return f"""          <filter class='categorical' column='[{ds}].[none:YrMo:nk]'>
            <groupfilter function='union' user:op='manual'>
{members}
            </groupfilter>
          </filter>"""


def share_lines():
    deps = "\n".join("            " + x for x in [
        inst("brokerage", "None", "nk"), inst("month", "Month-Trunc"), inst("share_pct", "Sum")])
    filters = brand_filter(BM, BRANDS_SHOWN)
    slices = f"            <column>[{BM}].[none:brokerage:nk]</column>"
    panes = f"""          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Line' />
            <encodings>
              <color column='[{BM}].[none:brokerage:nk]' />
              <text column='[{BM}].[none:brokerage:nk]' />
            </encodings>
{LINE_END_LABELS}
          </pane>"""
    return sheet("Brokerage Share", BM,
                 "Share of California listing sides by brokerage, monthly (sentinels excluded; Others omitted)",
                 deps, filters, slices, panes, f"[{BM}].[sum:share_pct:qk]", f"[{BM}].[tmn:month:qk]",
                 style="        <style />")


def opendoor_bars():
    deps = "\n".join("            " + x for x in [
        inst("brokerage", "None", "nk"), inst("month", "Month-Trunc"), inst("sides", "Sum")])
    filters = brand_filter(BM, ["Opendoor"])
    slices = f"            <column>[{BM}].[none:brokerage:nk]</column>"
    panes = f"""          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Bar' />
            <encodings>
              <text column='[{BM}].[sum:sides:qk]' />
            </encodings>
            <style>
              <style-rule element='mark'>
                <format attr='mark-labels-show' value='true' />
                <format attr='mark-labels-cull' value='true' />
                <format attr='mark-labels-mode' value='all' />
              </style-rule>
            </style>
          </pane>"""
    return sheet("Opendoor Listing Sides", BM,
                 "Opendoor listing sides per month -- the iBuyer's exit (2026 = first half only)",
                 deps, filters, slices, panes, f"[{BM}].[sum:sides:qk]", f"[{BM}].[tmn:month:qk]",
                 style="        <style />")


H1_2026 = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
Y2024 = [f"2024-{m:02d}" for m in range(1, 13)]


def kpi(name, title, measure_inst, measure_col, deriv, brands, months):
    deps = "\n".join("            " + x for x in [
        inst("brokerage", "None", "nk"), inst("YrMo", "None", "nk"), inst(measure_col, deriv)])
    filters = brand_filter(BM, brands) + "\n" + month_filter(BM, months)
    slices = f"            <column>[{BM}].[none:brokerage:nk]</column>\n            <column>[{BM}].[none:YrMo:nk]</column>"
    panes = f"""          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Automatic' />
            <encodings>
              <text column='[{BM}].{measure_inst}' />
            </encodings>
            <style>
              <style-rule element='mark'>
                <format attr='mark-labels-show' value='true' />
              </style-rule>
            </style>
          </pane>"""
    style = """        <style>
          <style-rule element='cell'>
            <format attr='text-align' value='center' />
            <format attr='font-weight' value='bold' />
            <format attr='font-size' value='24' />
          </style-rule>
          <style-rule element='table-div'>
            <format attr='line-visibility' scope='cols' value='off' />
            <format attr='line-visibility' scope='rows' value='off' />
          </style-rule>
        </style>"""
    return sheet(name, BM, title, deps, filters, slices, panes, "", "", style=style).replace(
        "<rows></rows>", "<rows />").replace("<cols></cols>", "<cols />")


# --------------------------------------------------------------- dashboards
def px(x, y, w, h):
    return dict(x=int(x * 100), y=int(y * 125), w=int(w * 100), h=int(h * 125))


class Dash:
    def __init__(self, name, note):
        self.name, self.note, self.zones, self.sheets, self.next_id = name, note, [], [], 2

    def _id(self):
        self.next_id += 1
        return self.next_id

    def sheet(self, s, x, y, w, h):
        b = px(x, y, w, h)
        self.sheets.append(s)
        self.zones.append(f"          <zone h='{b['h']}' id='{self._id()}' name='{s}' w='{b['w']}' x='{b['x']}' y='{b['y']}' />")

    def card(self, ds, dim, s, x, y, w, h):
        b = px(x, y, w, h)
        self.zones.append(f"          <zone h='{b['h']}' id='{self._id()}' mode='checkdropdown' name='{s}' "
                          f"param='[{ds}].[none:{dim}:nk]' type-v2='filter' w='{b['w']}' x='{b['x']}' y='{b['y']}' />")

    def xml(self):
        n = px(0, 770, 1000, 30)
        return f"""    <dashboard name='{self.name}'>
      <style />
      <size maxheight='800' maxwidth='1000' minheight='800' minwidth='1000' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='{n['h']}' id='2' type-v2='text' w='{n['w']}' x='{n['x']}' y='{n['y']}'>
            <formatted-text><run fontsize='8'>{self.note}</run></formatted-text>
          </zone>
{chr(10).join(self.zones)}
        </zone>
      </zones>
    </dashboard>"""


def window(kind, name, hidden=False, sheets=(), first=False):
    if kind == "worksheet":
        return f"""    <window class='worksheet'{" hidden='true'" if hidden else ""} name='{name}'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
      </cards>
      <viewpoint />
    </window>"""
    SCROLL = set()
    vps = "\n".join((f"        <viewpoint name='{s}' />" if s in SCROLL else
                     f"        <viewpoint name='{s}'>\n          <zoom type='entire-view' />\n        </viewpoint>")
                    for s in dict.fromkeys(sheets))
    return f"""    <window class='dashboard'{" maximized='true'" if first else ""} name='{name}'>
      <viewpoints>
{vps}
      </viewpoints>
      <active id='-1' />
    </window>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-sheets", action="store_true")
    args = ap.parse_args()

    ws = [
        agents_bars("Agents by Units", "units"),
        agents_bars("Agents by Volume", "volume"),
        offices_bars("Offices by Units", "units"),
        offices_bars("Offices by Volume", "volume"),
        zip_map("Zip Map - Median Price", "Median close price by zip code (color = median price, size = homes sold)",
                "[med:ClosePrice:qk]", "ClosePrice", "Median"),
        zip_map("Zip Map - Homes Sold", "Homes sold by zip code (color and size = homes sold)",
                "[sum:unit:qk]", "unit", "Sum"),
        share_lines(),
        opendoor_bars(),
        kpi("KPI Compass Share", "Compass share of listing sides, 2026 H1", "[avg:share_pct:qk]", "share_pct", "Avg", ["Compass"], H1_2026),
        kpi("KPI Compass Volume", "Compass sales volume, 2024", "[sum:volume:qk]", "volume", "Sum", ["Compass"], Y2024),
        kpi("KPI Real Broker Share", "Real Broker share of listing sides, 2026 H1", "[avg:share_pct:qk]", "share_pct", "Avg", ["Real Broker"], H1_2026),
        kpi("KPI Opendoor Sides", "Opendoor listing sides, 2026 H1", "[sum:sides:qk]", "sides", "Sum", ["Opendoor"], H1_2026),
    ]
    names = [w.split("name='")[1].split("'")[0] for w in ws]

    note_state = ("CRMLS sold, Jan 2024 - Jun 2026, 455,449 closed sales; 255 placeholder records (NONMEMBER etc.) "
                  "excluded from rankings and share denominators. Units = closed sales; volume = sum of close price.")
    note_geo = note_state + " Filters apply to every view on this tab."
    note_map = ("CRMLS sold, Jan 2024 - Jun 2026. One circle per zip code at the mean coordinates of its sales "
                "(88% of rows carry coordinates); color = the measure, size = homes sold. Filters apply to the map.")
    note_brok = ("Brokerage brands resolved from normalized office names (Compass / Keller Williams / Coldwell Banker / "
                 "RE/MAX / eXp / Berkshire / Century 21 / Sotheby's / Redfin / Real Broker / Equity Union / Opendoor / "
                 "Others). Share = brand listing sides / all listing sides that month. 2026 is January-June only.")

    d1 = Dash("Top 100 Agents", note_state)
    d1.sheet("Agents by Volume", 0, 0, 780, 385)
    d1.sheet("Agents by Units", 0, 385, 780, 385)
    d1.card(AG, "band_volume", "Agents by Volume", 780, 0, 220, 60)
    d1.card(AG, "band_units", "Agents by Units", 780, 385, 220, 60)

    d2 = Dash("Top 100 Offices", note_geo)
    d2.sheet("Offices by Volume", 0, 0, 780, 385)
    d2.sheet("Offices by Units", 0, 385, 780, 385)
    d2.card(SOLD, "office_band_volume", "Offices by Volume", 780, 0, 220, 60)
    d2.card(SOLD, "office_band_units", "Offices by Units", 780, 60, 220, 60)
    for i, dim in enumerate(["PostalCode", "PropertySubType", "CountyOrParish", "City"]):
        d2.card(SOLD, dim, "Offices by Volume", 780, 130 + i * 60, 220, 60)

    d3 = Dash("Zip Code Heatmaps", note_map)
    d3.sheet("Zip Map - Median Price", 0, 0, 780, 385)
    d3.sheet("Zip Map - Homes Sold", 0, 385, 780, 385)
    for i, dim in enumerate(["YrMo", "PostalCode", "PropertySubType", "CountyOrParish", "City"]):
        d3.card(SOLD, dim, "Zip Map - Median Price", 780, i * 55, 220, 55)

    d7 = Dash("Brokerage Power", note_brok)
    for i, k in enumerate(["KPI Compass Share", "KPI Compass Volume", "KPI Real Broker Share", "KPI Opendoor Sides"]):
        d7.sheet(k, i * 250, 0, 250, 150)
    d7.sheet("Brokerage Share", 0, 150, 620, 620)
    d7.sheet("Opendoor Listing Sides", 620, 150, 380, 620)

    dbs = [d1, d2, d3, d7]
    windows = [window("dashboard", d.name, sheets=d.sheets, first=(i == 0)) for i, d in enumerate(dbs)]
    windows += [window("worksheet", n, hidden=not args.show_sheets) for n in names]

    xml = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='{BUILD}' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <datasources>
{datasource(SOLD, 'competitive_sold.hyper', SOLD_COLS)}
{datasource(AG, 'top_agents.hyper', AG_COLS)}
{datasource(BM, 'brokerage_monthly.hyper', BM_COLS)}
  </datasources>
  <worksheets>
{chr(10).join(ws)}
  </worksheets>
  <dashboards>
{chr(10).join(d.xml() for d in dbs)}
  </dashboards>
  <windows>
{chr(10).join(windows)}
  </windows>
</workbook>
"""
    with open(OUT, "w") as fh:
        fh.write(xml)
    print(f"wrote {OUT} ({len(xml.splitlines())} lines): {len(ws)} worksheets, {len(dbs)} dashboards, "
          f"sheets {'visible' if args.show_sheets else 'hidden'}")


if __name__ == "__main__":
    main()
