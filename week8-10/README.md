# Weeks 8–10 — Tableau Dashboard Development

**Goal:** the two required Tableau workbooks — `market_analysis.twbx` (this folder, Week 8 ✅) and `competitive_analysis.twbx` (Weeks 9–10, upcoming) — built as **workbooks-as-code**: Python generates the data extracts and the workbook XML, Tableau just opens the result.

## What's in this folder

| File | What it is |
|---|---|
| `make_extracts.py` | Packages the Week 7 flagged datasets into Tableau's native extract format: `market_sold.hyper` (455,449 rows × 13 cols) and `market_listings.hyper` (504,162 × 8), including precomputed rank columns (county by closed sales, property type by listings) so ranked bar charts need only a range filter. Dates land as true dates — string months would sort alphabetically (Apr, Aug, Dec…), a classic silent bug. |
| `make_market_workbook.py` | Writes `market_analysis.twb` from scratch: 2 embedded-extract datasources, 13 worksheets (charts + KPI tiles), 6 geography-organized dashboards at Fixed 1000×800, linked filter cards, direct labels, provenance notes. `--show-sheets` builds a dev copy with worksheets visible. |
| `market_analysis.twb` | The generated workbook **structure** — pure XML, verified to contain **zero data rows**, which is why it can live in a public repo. The data-bearing `.twbx` and `.hyper` files are gitignored and stay local. |

## The six dashboards (v2 — the program's dashboard standard)

Rebuilt Aug 27 to the director's published standard and reference workbook: **desktop Fixed 1000×800**, dashboards organized by **geography** with 3–5 charts each, **KPI tiles top-left**, **one dropdown driving every chart on the tab** (Tableau's `filter-group` linkage, generated), **direct rounded labels** ($0.82M / 0.995 / 27), and **worksheets hidden** so only the dashboards publish as tabs.

| Tab | The one question it answers | What's on it |
|---|---|---|
| **Market Pulse** | What is the California market doing right now, and where? | 4 KPIs (median price, closed sales, avg DOM, avg ratio) · median price by month · closed sales by month · top-15 counties by closed sales (ranked) |
| **County** | How is the selected county trending? | County + property-type dropdowns · 4 KPIs · median price · close-to-list ratio · days on market · closed sales |
| **City** | How is the selected city trending? | County + City + property-type dropdowns · same stack |
| **Zip** | How is the selected zip trending? | County + Zip + property-type dropdowns · same stack |
| **New Listings** | How much new supply is coming, and of what type? | 4 dropdowns (listings data) · KPI · new listings by month · top-8 property types (ranked) |
| **Rates and the Market** (own design) | Do CA prices move with the national 30-yr mortgage rate? | median price and the FRED rate as **two stacked panes** on a shared month axis — never a dual axis |

All five handbook-required monthly views (median close price, average DOM, average close-to-original-list ratio, new listings, closed sales) appear on the geography tabs, filterable by City / County / Zip / PropertySubType — the requirement attaches to the *views*, and organizing them by geography is how the director's own reference workbook does it.

**The nuance rule in one line:** medians and counts use *all* rows (counts must never silently lose 15% of real transactions); *averages* use the IQR-filtered base with a subtitle saying so, and the ratio additionally excludes 552 data-entry rows above 2× (0.14%, disclosed). Every tab carries a one-line provenance note.

## The six tabs, rendered

Market Pulse:

![Market Pulse](img/tab1_market_pulse.png)

County:

![County](img/tab2_county.png)

City:

![City](img/tab3_city.png)

Zip:

![Zip](img/tab4_zip.png)

New Listings:

![New Listings](img/tab5_new_listings.png)

Rates and the Market (own design):

![Rates and the Market](img/tab6_rates_and_the_market.png)

## How to run

```bash
pip install tableauhyperapi
python3 make_extracts.py           # writes the two .hyper extracts to ~/idx-exchange/tableau/
python3 make_market_workbook.py    # writes market_analysis.twb (add --show-sheets for a dev build)
open -a "Tableau Public" ~/idx-exchange/tableau/market_analysis.twb
```

## What it took — the five validator iterations

Hand-authoring Tableau's XML dialect surfaced five undocumented rules, each caught by the open-and-check loop (open the workbook, read Tableau's error/log, fix, regenerate):

1. `<workbook>` requires a `source-build` attribute
2. `<window>` elements require a `<cards>` block
3. Every dashboard `<zone>` requires an `id`
4. Two measures on a shelf join with `+`, not a space
5. **Dashboard zones use a 0–100,000 coordinate space** — zones written as 0–100 rendered at 0.1% size, making the dashboards look empty when they were actually microscopic

The last fixes came from **extracting ground truth from Tableau's own bundled Superstore workbook** instead of guessing: filter `level` attributes must reference column-*instance* names (`[none:City:nk]`, not `[City]`), quick filters need a `<slices>` shelf, and zone attributes are `type-v2`.

## Status & what's deliberately not here

- ✅ Workbook opens clean in Tableau Public 2026.2; KPI tiles read $0.82M / 455,449 / 27 days / 0.995 statewide (pipeline-matching); six dashboards with linked dropdowns, direct labels, and rounded formats, generated end-to-end by code.
- 🔧 Two more grammar rules learned in v2: a dashboard window must list a `viewpoint` for **every** sheet it contains (otherwise "sheet has no visual representation"), and a KPI tile is an empty-shelf sheet with the measure on Text and its font set at the worksheet `cell` level.
- 📤 **Publishing goes to Tableau Public** per the program's August 24 directive (show Tableau progress on Tableau Public rather than committing workbook files). Published per the program's guidance: worksheets hidden, dashboards only, desktop layout.
- ⏭️ Weeks 9–10: `competitive_analysis.twbx` — top-100 agents/offices (where the office-name normalization and NONMEMBER-sentinel exclusion get used), the two zip-code heat maps, and the competitive own-design dashboard.
