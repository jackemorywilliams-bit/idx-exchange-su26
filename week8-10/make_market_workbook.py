"""
Weeks 8-10 - Generate market_analysis.twb (code-authored workbook).

Structure (per council rulings):
  - 2 datasources with embedded .hyper extracts (sold + listings, FLAGGED base)
  - 6 worksheets: the 5 required monthly views + "Rates and the Market" own-design
  - 6 dashboards, one per view, each with the 4 required filter cards
    (City / CountyOrParish / PostalCode / PropertySubType) + a provenance note
  - Metric rules (locked): MEDIAN close price + both COUNTS on ALL rows;
    AVG DOM + AVG price ratio on any_iqr_outlier_flag = 0 only;
    month axes are true month-truncated dates (not YrMo strings).
  - Rates & the Market: two stacked panes (median price / national 30yr rate),
    shared month axis -- never a dual axis.

The .twb opens in Tableau Public 2026.2.1 (validated recipe: source-build attr,
cards block in windows, embedded extract elements). Saved locally only until the
confidentiality confirmation; Jack's manual step is File > Save (.twbx) and,
in Weeks 11-12, Save to Tableau Public.
"""

import os

TABLEAU_DIR = os.path.expanduser("~/idx-exchange/tableau")
OUT = os.path.join(TABLEAU_DIR, "market_analysis.twb")
BUILD = "20262.26.0708.1337"

SOLD_DS, LIST_DS = "federated.sold", "federated.listings"

SOLD_COLS = """
      <column datatype='date' name='[CloseDate]' role='dimension' type='ordinal' />
      <column datatype='string' name='[YrMo]' role='dimension' type='nominal' />
      <column datatype='real' name='[ClosePrice]' role='measure' type='quantitative' />
      <column datatype='real' name='[price_ratio]' role='measure' type='quantitative' />
      <column datatype='real' name='[days_on_market]' role='measure' type='quantitative' />
      <column datatype='string' name='[City]' role='dimension' type='nominal' />
      <column datatype='string' name='[CountyOrParish]' role='dimension' type='nominal' />
      <column datatype='string' name='[PostalCode]' role='dimension' type='nominal' />
      <column datatype='string' name='[PropertySubType]' role='dimension' type='nominal' />
      <column datatype='string' name='[DistrictName]' role='dimension' type='nominal' />
      <column datatype='integer' name='[any_iqr_outlier_flag]' role='dimension' type='ordinal' />
      <column datatype='real' name='[rate_30yr_fixed]' role='measure' type='quantitative' />"""

LIST_COLS = """
      <column datatype='date' name='[ListingContractDate]' role='dimension' type='ordinal' />
      <column datatype='string' name='[ListYrMo]' role='dimension' type='nominal' />
      <column datatype='string' name='[City]' role='dimension' type='nominal' />
      <column datatype='string' name='[CountyOrParish]' role='dimension' type='nominal' />
      <column datatype='string' name='[PostalCode]' role='dimension' type='nominal' />
      <column datatype='string' name='[PropertySubType]' role='dimension' type='nominal' />
      <column datatype='integer' name='[any_iqr_outlier_flag]' role='dimension' type='ordinal' />"""


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


FILTER_DIMS = ["City", "CountyOrParish", "PostalCode", "PropertySubType"]


def filter_deps(ds):
    cols = "\n".join(
        f"            <column-instance column='[{d}]' derivation='None' "
        f"name='[none:{d}:nk]' pivot='key' type='nominal' />" for d in FILTER_DIMS)
    filts = "\n".join(
        f"          <filter class='categorical' column='[{ds}].[none:{d}:nk]'>"
        f"<groupfilter function='level-members' level='[{d}]' /></filter>"
        for d in FILTER_DIMS)
    return cols, filts


def worksheet(name, ds, caption, date_col, measure_inst, measure_col, measure_dt,
              mark, iqr_only, extra_rows_inst=""):
    filter_cols, filter_elems = filter_deps(ds)
    iqr_dep = iqr_filter = ""
    if iqr_only:
        iqr_dep = ("            <column-instance column='[any_iqr_outlier_flag]' "
                   "derivation='None' name='[none:any_iqr_outlier_flag:ok]' "
                   "pivot='key' type='ordinal' />")
        iqr_filter = (f"          <filter class='categorical' "
                      f"column='[{ds}].[none:any_iqr_outlier_flag:ok]'>"
                      f"<groupfilter function='member' "
                      f"level='[any_iqr_outlier_flag]' member='0' /></filter>")
    rows_expr = f"[{ds}].{measure_inst}" + (f" [{ds}].{extra_rows_inst}" if extra_rows_inst else "")
    return f"""    <worksheet name='{name}'>
      <layout-options>
        <title>
          <formatted-text><run>{caption}</run></formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{ds}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            <column datatype='date' name='[{date_col}]' role='dimension' type='ordinal' />
            <column datatype='{measure_dt}' name='[{measure_col}]' role='{"dimension" if measure_dt == "string" else "measure"}' type='{"nominal" if measure_dt == "string" else "quantitative"}' />
{filter_cols}
{iqr_dep}
            <column-instance column='[{date_col}]' derivation='Month-Trunc' name='[tmn:{date_col}:qk]' pivot='key' type='quantitative' />
            {measure_inst_decl(measure_inst, measure_col)}
            {measure_inst_decl(extra_rows_inst, 'rate_30yr_fixed') if extra_rows_inst else ''}
          </datasource-dependencies>
{filter_elems}
{iqr_filter}
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='{mark}' />
          </pane>
        </panes>
        <rows>{rows_expr}</rows>
        <cols>[{ds}].[tmn:{date_col}:qk]</cols>
      </table>
    </worksheet>"""


def measure_inst_decl(inst, col):
    if not inst:
        return ""
    deriv = {"med": "Median", "avg": "Avg", "cnt": "Count"}[inst.split(":")[0][1:]]
    return (f"<column-instance column='[{col}]' derivation='{deriv}' "
            f"name='{inst}' pivot='key' type='quantitative' />")


def dashboard(name, sheet, ds, note):
    filter_zones = "\n".join(
        f"          <zone h='8' id='{4 + i}' name='{sheet}' param='[{ds}].[none:{d}:nk]' "
        f"type='filter' w='16' x='84' y='{8 + i * 10}' />"
        for i, d in enumerate(FILTER_DIMS))
    return f"""    <dashboard name='{name}'>
      <style />
      <size maxheight='850' maxwidth='1250' minheight='850' minwidth='1250' />
      <zones>
        <zone h='100' id='1' type='layout-basic' w='100' x='0' y='0'>
          <zone h='6' id='2' type='text' w='84' x='0' y='0'>
            <formatted-text><run>{note}</run></formatted-text>
          </zone>
          <zone h='94' id='3' name='{sheet}' w='84' x='0' y='6' />
{filter_zones}
        </zone>
      </zones>
    </dashboard>"""


def main():
    ws = []
    ws.append(worksheet("Monthly Median Close Price", SOLD_DS,
                        "Monthly Median Close Price (all sold rows)",
                        "CloseDate", "[med:ClosePrice:qk]", "ClosePrice", "real",
                        "Line", iqr_only=False))
    ws.append(worksheet("Average Days on Market", SOLD_DS,
                        "Average Days on Market - mean of MLS days_on_market, IQR-filtered",
                        "CloseDate", "[avg:days_on_market:qk]", "days_on_market", "real",
                        "Line", iqr_only=True))
    ws.append(worksheet("Average Close-to-Original-List Ratio", SOLD_DS,
                        "Avg Close-to-Original-List Ratio - AVG of per-sale ratio, IQR-filtered",
                        "CloseDate", "[avg:price_ratio:qk]", "price_ratio", "real",
                        "Line", iqr_only=True))
    ws.append(worksheet("New Listings", LIST_DS,
                        "New Listings per Month (by listing contract date, all rows)",
                        "ListingContractDate", "[cnt:ListYrMo:qk]", "ListYrMo", "string",
                        "Bar", iqr_only=False))
    ws.append(worksheet("Closed Sales", SOLD_DS,
                        "Closed Sales per Month (all sold rows)",
                        "CloseDate", "[cnt:ClosePrice:qk]", "ClosePrice", "real",
                        "Bar", iqr_only=False))
    ws.append(worksheet("Rates and the Market", SOLD_DS,
                        "Median Close Price vs National 30-yr Mortgage Rate (stacked panes)",
                        "CloseDate", "[med:ClosePrice:qk]", "ClosePrice", "real",
                        "Line", iqr_only=False, extra_rows_inst="[avg:rate_30yr_fixed:qk]"))

    prov_sold = ("CRMLS sold, Jan 2024 - Jun 2026, N=455,449. Medians and counts use "
                 "all rows; averages are IQR-filtered (~15% excluded).")
    prov_list = ("CRMLS listings, Jan 2024 - Jun 2026, N=504,162 (all rows -- counts "
                 "are never outlier-filtered).")
    prov_rates = (prov_sold + " 30-yr rate is the U.S. national monthly average, "
                  "not CA-specific; geographic filters move only the price line.")
    dbs = [
        dashboard("DB Monthly Median Close Price", "Monthly Median Close Price", SOLD_DS, prov_sold),
        dashboard("DB Average Days on Market", "Average Days on Market", SOLD_DS, prov_sold),
        dashboard("DB Avg Close-to-Original-List Ratio", "Average Close-to-Original-List Ratio", SOLD_DS, prov_sold),
        dashboard("DB New Listings", "New Listings", LIST_DS, prov_list),
        dashboard("DB Closed Sales", "Closed Sales", SOLD_DS, prov_sold),
        dashboard("DB Rates and the Market", "Rates and the Market", SOLD_DS, prov_rates),
    ]

    xml = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='{BUILD}' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <datasources>
{datasource(SOLD_DS, 'Market Sold (Flagged)', 'market_sold.hyper', SOLD_COLS)}
{datasource(LIST_DS, 'Market Listings (Flagged)', 'market_listings.hyper', LIST_COLS)}
  </datasources>
  <worksheets>
{chr(10).join(ws)}
  </worksheets>
  <dashboards>
{chr(10).join(dbs)}
  </dashboards>
  <windows>
    <window class='worksheet' maximized='true' name='Monthly Median Close Price'>
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
    </window>
  </windows>
</workbook>
"""
    with open(OUT, "w") as fh:
        fh.write(xml)
    print(f"wrote {OUT} ({len(xml.splitlines())} lines)")


if __name__ == "__main__":
    main()


# RUN LOG (observed)
# -----------------------------------------------------------------------------
# wrote ~/idx-exchange/tableau/market_analysis.twb (426 lines).
# Opened in Tableau Public 2026.2.1 with no fresh validator errors in
# ~/Documents/My Tableau Repository/Logs. Structure: 2 embedded-extract
# datasources (sold flagged 455,449 / listings flagged 504,162), 6 worksheets,
# 6 single-view dashboards each carrying the 4 required filter cards + a
# provenance note. Metric bases per locked rules: medians/counts all rows;
# AVG DOM + AVG ratio on any_iqr_outlier_flag=0. NOT published anywhere --
# local only pending the confidentiality confirmation.
# =============================================================================
