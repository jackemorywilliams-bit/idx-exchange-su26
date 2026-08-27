"""
Weeks 8-10 - Generate market_analysis.twb (code-authored workbook), v2.

v2 re-organizes the workbook to the program's dashboard standard (director's
Aug 21 guidance + his reference workbook): desktop Fixed 1000x800, dashboards
organized by GEOGRAPHY with 3-5 charts each, KPI tiles top-left, one dropdown
driving every chart on the tab (filter-group linkage), direct rounded labels
($0.78M / 1.012 / 25), worksheets hidden so only dashboards publish as tabs.

Tabs
  Market Pulse   statewide KPIs + median price + closed sales + top-15 counties
  County         County dropdown -> KPIs + median / ratio / DOM / closed sales
  City           County + City dropdowns -> same stack
  Zip            County + Zip dropdowns -> same stack
  New Listings   listings datasource: KPI + monthly bars + by property type
  Rates and the Market   own design: median price vs national 30-yr rate

Locked metric rules carried over: MEDIAN price + COUNTS on ALL rows; AVG DOM and
AVG ratio on any_iqr_outlier_flag = 0; the ratio additionally bounded to (0, 2]
(552 data-entry rows, 0.14%, disclosed in the subtitle); month axes are true
month-truncated dates; "Avg DOM" is the MLS system field.

Run:  python3 make_market_workbook.py            (worksheets hidden = publish build)
      python3 make_market_workbook.py --show-sheets   (dev build, sheets visible)
"""

import argparse
import os

TABLEAU_DIR = os.path.expanduser("~/idx-exchange/tableau")
OUT = os.path.join(TABLEAU_DIR, "market_analysis.twb")
BUILD = "20262.26.0708.1337"

SOLD_DS, LIST_DS = "federated.sold", "federated.listings"
SOLD_CAP, LIST_CAP = "Market Sold (Flagged)", "Market Listings (Flagged)"

# Tableau number-format codes (copied from the bundled Superstore workbook).
FMT_MONEY_M = "c&quot;$&quot;#,##0,,.00M;(&quot;$&quot;#,##0,,.00M)"
FMT_RATIO = "n#,##0.000;-#,##0.000"
FMT_INT = "n#,##0;-#,##0"
FMT_PCT2 = "n#,##0.00&quot;%&quot;;-#,##0.00&quot;%&quot;"

SOLD_COLS = f"""
      <column caption='Close Date' datatype='date' name='[CloseDate]' role='dimension' type='ordinal' />
      <column caption='Closed Sale' datatype='string' name='[YrMo]' role='dimension' type='nominal' />
      <column caption='Close Price' datatype='real' default-format='{FMT_MONEY_M}' name='[ClosePrice]' role='measure' type='quantitative' />
      <column caption='Close-to-List Ratio' datatype='real' default-format='{FMT_RATIO}' name='[price_ratio]' role='measure' type='quantitative' />
      <column caption='Days on Market' datatype='real' default-format='{FMT_INT}' name='[days_on_market]' role='measure' type='quantitative' />
      <column datatype='string' name='[City]' role='dimension' type='nominal' />
      <column caption='County' datatype='string' name='[CountyOrParish]' role='dimension' type='nominal' />
      <column caption='Zip Code' datatype='string' name='[PostalCode]' role='dimension' type='nominal' />
      <column caption='Property Type' datatype='string' name='[PropertySubType]' role='dimension' type='nominal' />
      <column datatype='string' name='[DistrictName]' role='dimension' type='nominal' />
      <column datatype='integer' name='[any_iqr_outlier_flag]' role='dimension' type='ordinal' />
      <column caption='30-yr Mortgage Rate' datatype='real' default-format='{FMT_PCT2}' name='[rate_30yr_fixed]' role='measure' type='quantitative' />
      <column caption='Rank' datatype='integer' name='[county_sold_rank]' role='dimension' type='ordinal' />"""

LIST_COLS = """
      <column caption='Listing Date' datatype='date' name='[ListingContractDate]' role='dimension' type='ordinal' />
      <column caption='New Listing' datatype='string' name='[ListYrMo]' role='dimension' type='nominal' />
      <column datatype='string' name='[City]' role='dimension' type='nominal' />
      <column caption='County' datatype='string' name='[CountyOrParish]' role='dimension' type='nominal' />
      <column caption='Zip Code' datatype='string' name='[PostalCode]' role='dimension' type='nominal' />
      <column caption='Property Type' datatype='string' name='[PropertySubType]' role='dimension' type='nominal' />
      <column datatype='integer' name='[any_iqr_outlier_flag]' role='dimension' type='ordinal' />
      <column caption='Rank' datatype='integer' name='[listing_subtype_rank]' role='dimension' type='ordinal' />"""

FILTER_DIMS = ["CountyOrParish", "City", "PostalCode", "PropertySubType"]
# filter-group ids link one quick-filter card to every sheet carrying the same
# field filter (this is how Tableau stores "apply to all using this data source").
FILTER_GROUP = {SOLD_DS: {d: i + 1 for i, d in enumerate(FILTER_DIMS)},
                LIST_DS: {d: i + 5 for i, d in enumerate(FILTER_DIMS)}}

LABEL_STYLE = """            <style>
              <style-rule element='mark'>
                <format attr='mark-labels-show' value='true' />
                <format attr='mark-labels-cull' value='true' />
                <format attr='mark-labels-mode' value='all' />
              </style-rule>
            </style>"""


def datasource(name, caption, hyper, cols):
    return f"""    <datasource caption='{caption}' inline='true' name='{name}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='{caption}' name='hyper.{name}'>
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


def filter_deps(ds):
    cols = "\n".join(
        f"            <column-instance column='[{d}]' derivation='None' "
        f"name='[none:{d}:nk]' pivot='key' type='nominal' />" for d in FILTER_DIMS)
    filts = "\n".join(
        f"          <filter class='categorical' column='[{ds}].[none:{d}:nk]' "
        f"filter-group='{FILTER_GROUP[ds][d]}'>"
        f"<groupfilter function='level-members' level='[none:{d}:nk]' "
        f"user:ui-enumeration='all' user:ui-marker='enumerate' /></filter>"
        for d in FILTER_DIMS)
    slices = "\n".join(f"            <column>[{ds}].[none:{d}:nk]</column>" for d in FILTER_DIMS)
    return cols, filts, slices


def measure_inst_decl(inst, col):
    if not inst:
        return ""
    deriv = {"med": "Median", "avg": "Avg", "cnt": "Count"}[inst.split(":")[0][1:]]
    return (f"<column-instance column='[{col}]' derivation='{deriv}' "
            f"name='{inst}' pivot='key' type='quantitative' />")


def base_filters(ds, iqr_only, ratio_bound):
    """Column-instance decls, filter elements and slice columns shared by sheets."""
    filter_cols, filter_elems, slice_cols = filter_deps(ds)
    deps, filts = filter_cols, filter_elems
    if iqr_only:
        deps += ("\n            <column-instance column='[any_iqr_outlier_flag]' "
                 "derivation='None' name='[none:any_iqr_outlier_flag:ok]' "
                 "pivot='key' type='ordinal' />")
        filts += (f"\n          <filter class='categorical' "
                  f"column='[{ds}].[none:any_iqr_outlier_flag:ok]'>"
                  f"<groupfilter function='member' "
                  f"level='[none:any_iqr_outlier_flag:ok]' member='0' /></filter>")
        slice_cols += f"\n            <column>[{ds}].[none:any_iqr_outlier_flag:ok]</column>"
    if ratio_bound:
        # The IQR flag fences price/area/DOM but NOT the ratio itself; 552
        # IQR-kept rows (0.14%) carry data-entry ratios above 2x (max 1.08M x).
        deps += ("\n            <column-instance column='[price_ratio]' "
                 "derivation='None' name='[none:price_ratio:qk]' "
                 "pivot='key' type='quantitative' />")
        filts += (f"\n          <filter class='quantitative' "
                  f"column='[{ds}].[none:price_ratio:qk]' "
                  f"included-values='in-range'><min>0</min><max>2</max></filter>")
        slice_cols += f"\n            <column>[{ds}].[none:price_ratio:qk]</column>"
    return deps, filts, slice_cols


CAPTIONS = {'ClosePrice': 'Close Price', 'price_ratio': 'Close-to-List Ratio', 'days_on_market': 'Days on Market', 'rate_30yr_fixed': '30-yr Mortgage Rate', 'YrMo': 'Closed Sale', 'ListYrMo': 'New Listing', 'county_sold_rank': 'Rank', 'listing_subtype_rank': 'Rank', 'CountyOrParish': 'County', 'PostalCode': 'Zip Code', 'PropertySubType': 'Property Type', 'ListingContractDate': 'Listing Date', 'CloseDate': 'Close Date'}


def col_decl(col, dt):
    role = "dimension" if dt in ("string", "integer", "date") else "measure"
    typ = {"string": "nominal", "integer": "ordinal", "date": "ordinal"}.get(dt, "quantitative")
    cap = f"caption='{CAPTIONS[col]}' " if col in CAPTIONS else ""
    return f"<column {cap}datatype='{dt}' name='[{col}]' role='{role}' type='{typ}' />"


def month_sheet(name, ds, caption, date_col, measure_inst, measure_col, measure_dt,
                mark, iqr_only=False, ratio_bound=False, extra_rows_inst="", labels=True):
    """A monthly time-series sheet (line or bar) with the 4 linked filters."""
    caption_ds = SOLD_CAP if ds == SOLD_DS else LIST_CAP
    deps, filts, slices = base_filters(ds, iqr_only, ratio_bound)
    rows_expr = f"[{ds}].{measure_inst}" + (f" + [{ds}].{extra_rows_inst}" if extra_rows_inst else "")
    text_enc = (f"            <encodings>\n              <text column='[{ds}].{measure_inst}' />\n"
                f"            </encodings>\n{LABEL_STYLE}") if labels and not extra_rows_inst else ""
    return f"""    <worksheet name='{name}'>
      <layout-options>
        <title>
          <formatted-text><run>{caption}</run></formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{caption_ds}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            {col_decl(date_col, 'date')}
            {col_decl(measure_col, measure_dt)}
            {col_decl('rate_30yr_fixed', 'real') if extra_rows_inst else ''}
{deps}
            <column-instance column='[{date_col}]' derivation='Month-Trunc' name='[tmn:{date_col}:qk]' pivot='key' type='quantitative' />
            {measure_inst_decl(measure_inst, measure_col)}
            {measure_inst_decl(extra_rows_inst, 'rate_30yr_fixed') if extra_rows_inst else ''}
          </datasource-dependencies>
{filts}
          <slices>
{slices}
          </slices>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='{mark}' />
{text_enc}
          </pane>
        </panes>
        <rows>{rows_expr}</rows>
        <cols>[{ds}].[tmn:{date_col}:qk]</cols>
      </table>
    </worksheet>"""


def ban_sheet(name, ds, caption, measure_inst, measure_col, measure_dt,
              iqr_only=False, ratio_bound=False):
    """A single-number KPI tile: empty shelves, one aggregated measure on Text."""
    caption_ds = SOLD_CAP if ds == SOLD_DS else LIST_CAP
    deps, filts, slices = base_filters(ds, iqr_only, ratio_bound)
    return f"""    <worksheet name='{name}'>
      <layout-options>
        <title>
          <formatted-text><run fontsize='10'>{caption}</run></formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{caption_ds}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            {col_decl(measure_col, measure_dt)}
{deps}
            {measure_inst_decl(measure_inst, measure_col)}
          </datasource-dependencies>
{filts}
          <slices>
{slices}
          </slices>
          <aggregation value='true' />
        </view>
        <style>
          <style-rule element='cell'>
            <format attr='text-align' value='center' />
            <format attr='font-weight' value='bold' />
            <format attr='font-size' value='24' />
          </style-rule>
          <style-rule element='table-div'>
            <format attr='line-visibility' scope='cols' value='off' />
            <format attr='line-visibility' scope='rows' value='off' />
          </style-rule>
        </style>
        <panes>
          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Automatic' />
            <encodings>
              <text column='[{ds}].{measure_inst}' />
            </encodings>
            <style>
              <style-rule element='mark'>
                <format attr='mark-labels-show' value='true' />
              </style-rule>
            </style>
          </pane>
        </panes>
        <rows />
        <cols />
      </table>
    </worksheet>"""


def category_bar_sheet(name, ds, caption, dim, measure_inst, measure_col, measure_dt,
                       rank_top=None, rank_col="county_sold_rank"):
    """Horizontal bars of a count by a category; optional precomputed-rank cut."""
    caption_ds = SOLD_CAP if ds == SOLD_DS else LIST_CAP
    deps, filts, slices = base_filters(ds, False, False)
    rank_dep = rank_filter = rank_rows = ""
    if rank_top:
        rank_dep = (f"\n            <column-instance column='[{rank_col}]' derivation='None' "
                    f"name='[none:{rank_col}:qk]' pivot='key' type='quantitative' />"
                    f"\n            <column-instance column='[{rank_col}]' derivation='None' "
                    f"name='[none:{rank_col}:nk]' pivot='key' type='ordinal' />")
        rank_filter = (f"\n          <filter class='quantitative' column='[{ds}].[none:{rank_col}:qk]' "
                       f"included-values='in-range'><min>1</min><max>{rank_top}</max></filter>")
        slices += f"\n            <column>[{ds}].[none:{rank_col}:qk]</column>"
        rank_rows = f"[{ds}].[none:{rank_col}:nk] / "
    dim_dep = "" if dim in FILTER_DIMS else (
        f"\n            <column-instance column='[{dim}]' derivation='None' name='[none:{dim}:nk]' pivot='key' type='nominal' />")
    return f"""    <worksheet name='{name}'>
      <layout-options>
        <title>
          <formatted-text><run>{caption}</run></formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{caption_ds}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            {col_decl(measure_col, measure_dt)}
            {col_decl(rank_col, 'integer') if rank_top else ''}
{deps}{dim_dep}{rank_dep}
            {measure_inst_decl(measure_inst, measure_col)}
          </datasource-dependencies>
{filts}{rank_filter}
          <slices>
{slices}
          </slices>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Bar' />
            <encodings>
              <text column='[{ds}].{measure_inst}' />
            </encodings>
{LABEL_STYLE}
          </pane>
        </panes>
        <rows>({rank_rows}[{ds}].[none:{dim}:nk])</rows>
        <cols>[{ds}].{measure_inst}</cols>
      </table>
    </worksheet>"""


# ----------------------------------------------------------------------------
# Dashboards: Fixed 1000x800. Zone coords are in Tableau's 0-100,000 space, so
# x-units = px * 100 and y-units = px * 125. Helpers take pixel boxes.
# ----------------------------------------------------------------------------

def px(x, y, w, h):
    return dict(x=int(x * 100), y=int(y * 125), w=int(w * 100), h=int(h * 125))


class Dash:
    def __init__(self, name, note):
        self.name, self.note, self.zones, self.sheets, self.next_id = name, note, [], [], 2

    def _id(self):
        self.next_id += 1
        return self.next_id

    def sheet(self, sheet, x, y, w, h):
        b = px(x, y, w, h)
        self.sheets.append(sheet)
        self.zones.append(f"          <zone h='{b['h']}' id='{self._id()}' name='{sheet}' "
                          f"w='{b['w']}' x='{b['x']}' y='{b['y']}' />")

    def card(self, ds, dim, sheet, x, y, w, h):
        b = px(x, y, w, h)
        self.zones.append(f"          <zone h='{b['h']}' id='{self._id()}' mode='checkdropdown' "
                          f"name='{sheet}' param='[{ds}].[none:{dim}:nk]' type-v2='filter' "
                          f"w='{b['w']}' x='{b['x']}' y='{b['y']}' />")

    def xml(self):
        n = px(0, 770, 1000, 30)
        note_zone = (f"          <zone h='{n['h']}' id='2' type-v2='text' w='{n['w']}' x='{n['x']}' y='{n['y']}'>\n"
                     f"            <formatted-text><run fontsize='8'>{self.note}</run></formatted-text>\n"
                     f"          </zone>")
        return f"""    <dashboard name='{self.name}'>
      <style />
      <size maxheight='800' maxwidth='1000' minheight='800' minwidth='1000' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
{note_zone}
{chr(10).join(self.zones)}
        </zone>
      </zones>
    </dashboard>"""


def geography_tab(name, dims, note):
    """County / City / Zip tabs: dropdown(s) + 4 KPI tiles + 4 charts."""
    d = Dash(name, note)
    top_h = 150
    card_h = top_h / (len(dims) + 1)
    for i, dim in enumerate(dims + ["PropertySubType"]):
        d.card(SOLD_DS, dim, "Median Close Price", 0, i * card_h, 200, card_h)
    for i, kpi in enumerate(["KPI Median Price", "KPI Closed Sales", "KPI Days on Market", "KPI Ratio"]):
        d.sheet(kpi, 200 + i * 200, 0, 200, top_h)
    chart_h = (770 - top_h) / 2
    d.sheet("Median Close Price", 0, top_h, 500, chart_h)
    d.sheet("Close-to-List Ratio", 500, top_h, 500, chart_h)
    d.sheet("Days on Market", 0, top_h + chart_h, 500, chart_h)
    d.sheet("Closed Sales", 500, top_h + chart_h, 500, chart_h)
    return d


def market_pulse(note):
    d = Dash("Market Pulse", note)
    d.card(SOLD_DS, "PropertySubType", "Median Close Price", 0, 0, 200, 75)
    d.card(SOLD_DS, "CountyOrParish", "Median Close Price", 0, 75, 200, 75)
    for i, kpi in enumerate(["KPI Median Price", "KPI Closed Sales", "KPI Days on Market", "KPI Ratio"]):
        d.sheet(kpi, 200 + i * 200, 0, 200, 150)
    d.sheet("Median Close Price", 0, 150, 500, 310)
    d.sheet("Closed Sales", 500, 150, 500, 310)
    d.sheet("Closed Sales by County", 0, 460, 1000, 310)
    return d


def new_listings_tab(note):
    d = Dash("New Listings", note)
    for i, dim in enumerate(FILTER_DIMS):
        d.card(LIST_DS, dim, "New Listings by Month", 0, i * 60, 220, 60)
    d.sheet("KPI New Listings", 220, 0, 200, 240)
    d.sheet("New Listings by Property Type", 420, 0, 580, 240)
    d.sheet("New Listings by Month", 0, 240, 1000, 530)
    return d


def rates_tab(note):
    d = Dash("Rates and the Market", note)
    d.card(SOLD_DS, "CountyOrParish", "Rates vs Median Price", 0, 0, 250, 75)
    d.card(SOLD_DS, "PropertySubType", "Rates vs Median Price", 0, 75, 250, 75)
    d.sheet("KPI Median Price", 250, 0, 375, 150)
    d.sheet("KPI Closed Sales", 625, 0, 375, 150)
    d.sheet("Rates vs Median Price", 0, 150, 1000, 620)
    return d


def window(kind, name, hidden=False, sheets=()):
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
    vps = "\n".join(f"        <viewpoint name='{s}'>\n          <zoom type='entire-view' />\n        </viewpoint>"
                    for s in dict.fromkeys(sheets))
    return f"""    <window class='dashboard'{" maximized='true'" if name == 'Market Pulse' else ""} name='{name}'>
      <viewpoints>
{vps}
      </viewpoints>
      <active id='-1' />
    </window>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-sheets", action="store_true", help="dev build: worksheets visible")
    args = ap.parse_args()

    ws = [
        month_sheet("Median Close Price", SOLD_DS, "Median Close Price by Month (all sold rows)",
                    "CloseDate", "[med:ClosePrice:qk]", "ClosePrice", "real", "Line"),
        month_sheet("Close-to-List Ratio", SOLD_DS,
                    "Avg Close-to-Original-List Ratio (IQR-filtered; ratios above 2 excluded: 552 rows, 0.14%)",
                    "CloseDate", "[avg:price_ratio:qk]", "price_ratio", "real", "Line",
                    iqr_only=True, ratio_bound=True),
        month_sheet("Days on Market", SOLD_DS, "Avg Days on Market (MLS field, IQR-filtered)",
                    "CloseDate", "[avg:days_on_market:qk]", "days_on_market", "real", "Line",
                    iqr_only=True),
        month_sheet("Closed Sales", SOLD_DS, "Closed Sales by Month (all sold rows)",
                    "CloseDate", "[cnt:YrMo:qk]", "YrMo", "string", "Bar"),
        month_sheet("New Listings by Month", LIST_DS, "New Listings by Month (listing contract date, all rows)",
                    "ListingContractDate", "[cnt:ListYrMo:qk]", "ListYrMo", "string", "Bar"),
        month_sheet("Rates vs Median Price", SOLD_DS,
                    "Median Close Price (top) vs National 30-yr Mortgage Rate (bottom)",
                    "CloseDate", "[med:ClosePrice:qk]", "ClosePrice", "real", "Line",
                    extra_rows_inst="[avg:rate_30yr_fixed:qk]"),
        category_bar_sheet("Closed Sales by County", SOLD_DS,
                           "Closed Sales, Top 15 Counties (ranked by total sales)",
                           "CountyOrParish", "[cnt:YrMo:qk]", "YrMo", "string", rank_top=15),
        category_bar_sheet("New Listings by Property Type", LIST_DS,
                           "New Listings by Property Type (top 8)", "PropertySubType",
                           "[cnt:ListYrMo:qk]", "ListYrMo", "string",
                           rank_top=8, rank_col="listing_subtype_rank"),
        ban_sheet("KPI Median Price", SOLD_DS, "Median Close Price", "[med:ClosePrice:qk]", "ClosePrice", "real"),
        ban_sheet("KPI Closed Sales", SOLD_DS, "Closed Sales", "[cnt:YrMo:qk]", "YrMo", "string"),
        ban_sheet("KPI Days on Market", SOLD_DS, "Avg Days on Market (IQR-filtered)",
                  "[avg:days_on_market:qk]", "days_on_market", "real", iqr_only=True),
        ban_sheet("KPI Ratio", SOLD_DS, "Avg Close-to-List Ratio (IQR-filtered)",
                  "[avg:price_ratio:qk]", "price_ratio", "real", iqr_only=True, ratio_bound=True),
        ban_sheet("KPI New Listings", LIST_DS, "New Listings", "[cnt:ListYrMo:qk]", "ListYrMo", "string"),
    ]
    sheet_names = [w.split("name='")[1].split("'")[0] for w in ws]

    prov_sold = ("CRMLS sold, Jan 2024 - Jun 2026, N=455,449. Medians and counts use all rows; "
                 "averages are IQR-filtered (~15% excluded). Filters apply to every chart on this tab.")
    prov_list = ("CRMLS listings, Jan 2024 - Jun 2026, N=504,162 (all rows; counts are never "
                 "outlier-filtered). Filters apply to every chart on this tab.")
    prov_rates = (prov_sold + " 30-yr rate = U.S. national monthly average (FRED), not CA-specific; "
                  "geographic filters move only the price line.")
    dbs = [
        market_pulse(prov_sold),
        geography_tab("County", ["CountyOrParish"], prov_sold),
        geography_tab("City", ["CountyOrParish", "City"], prov_sold),
        geography_tab("Zip", ["CountyOrParish", "PostalCode"], prov_sold),
        new_listings_tab(prov_list),
        rates_tab(prov_rates),
    ]

    windows = [window("dashboard", d.name, sheets=d.sheets) for d in dbs]
    windows += [window("worksheet", s, hidden=not args.show_sheets) for s in sheet_names]

    xml = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='{BUILD}' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <datasources>
{datasource(SOLD_DS, SOLD_CAP, 'market_sold.hyper', SOLD_COLS)}
{datasource(LIST_DS, LIST_CAP, 'market_listings.hyper', LIST_COLS)}
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
    print(f"wrote {OUT} ({len(xml.splitlines())} lines): {len(ws)} worksheets, "
          f"{len(dbs)} dashboards, sheets {'visible' if args.show_sheets else 'hidden'}")


if __name__ == "__main__":
    main()


# RUN LOG (observed)
# -----------------------------------------------------------------------------
# v1 (Aug 11-26): 6 single-chart dashboards, Custom 1250x850, 4 filter cards each.
# RATIO FIX (Aug 26): the IQR flag fences ClosePrice/LivingArea/DaysOnMarket but
# NOT price_ratio, so 552 IQR-kept rows (0.14%) with data-entry ratios above 2x
# (max 1,077,419x -- a $1 original list price) pushed monthly AVG(price_ratio)
# as high as 170.95. Median ratio is 1.0000, p75 1.0216; with the (0, 2] range
# filter the monthly average lands at 0.9811-1.0166. Disclosed in the subtitle.
# v2 (Aug 27): rebuilt to the program's dashboard standard -- see module docstring.
# =============================================================================
