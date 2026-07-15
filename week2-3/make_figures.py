"""
Generate the two README figures for the Weeks 2-3 deliverable:
  1. figures/columns_kept_dropped.png -- the 79 -> 31 column keep/drop breakdown.
  2. figures/mortgage_rate_30yr.png    -- the monthly 30yr fixed rate joined onto the data.

Colors come from the data-viz reference palette (validated categorical slots); charts
use a light surface, thin marks, recessive axes, and direct labels.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
FRED_CACHE = os.path.expanduser(
    "~/idx-exchange/deliverables/fred_mortgage30us_cache.csv")

# --- palette (light surface) --------------------------------------------------
SURFACE = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"
GRID = "#e1e0d9"; BLUE = "#2a78d6"; AQUA = "#1baf7a"; YELLOW = "#eda100"; ORANGE = "#eb6834"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2,
    "ytick.color": INK2, "axes.edgecolor": MUTED,
})

# The column-drop decision (79 -> 31), grouped by reason.
KEPT = [
    "ListingKey", "ClosePrice", "ListPrice", "OriginalListPrice", "CloseDate",
    "ListingContractDate", "PurchaseContractDate", "DaysOnMarket", "MlsStatus",
    "PropertyType", "PropertySubType", "LivingArea", "LotSizeSquareFeet",
    "BedroomsTotal", "BathroomsTotalInteger", "YearBuilt", "CountyOrParish", "City",
    "PostalCode", "StateOrProvince", "MLSAreaMajor", "Latitude", "Longitude",
    "ListOfficeName", "BuyerOfficeName", "ListAgentFullName", "ListAgentAOR",
    "BuyerAgentFirstName", "BuyerAgentLastName", "BuyerAgentMlsId", "BuyerAgentAOR",
]
DROP_NULL = [
    "WaterfrontYN", "BasementYN", "FireplacesTotal", "AboveGradeFinishedArea",
    "TaxAnnualAmount", "BuilderName", "TaxYear", "BuildingAreaTotal",
    "ElementarySchoolDistrict", "CoBuyerAgentFirstName", "BelowGradeFinishedArea",
    "BusinessType", "CoveredSpaces", "LotSizeDimensions", "MiddleOrJuniorSchoolDistrict",
]
DROP_REDUNDANT = [
    "ListingKeyNumeric", "ListingId", "LotSizeAcres", "LotSizeArea",
    "ListAgentFirstName", "ListAgentLastName", "UnparsedAddress", "StreetNumberNumeric",
    "OriginatingSystemName", "OriginatingSystemSubName",
]
DROP_NOTRELEVANT = [
    "Flooring", "ViewYN", "PoolPrivateYN", "CoListOfficeName", "CoListAgentFirstName",
    "CoListAgentLastName", "AssociationFeeFrequency", "ElementarySchool",
    "AttachedGarageYN", "ParkingTotal", "SubdivisionName", "BuyerOfficeAOR",
    "ContractStatusChangeDate", "MiddleOrJuniorSchool", "FireplaceYN", "Stories",
    "HighSchool", "Levels", "MainLevelBedrooms", "NewConstructionYN", "GarageSpaces",
    "HighSchoolDistrict", "AssociationFee",
]


def fig_columns():
    # Kept is the saturated color story; the three drop reasons are one muted
    # family (descending) so kept-vs-dropped reads at a glance.
    cats = ["Kept — dashboard fields", "Dropped — not dashboard-relevant",
            "Dropped — >90% null", "Dropped — redundant duplicate"]
    vals = [len(KEPT), len(DROP_NOTRELEVANT), len(DROP_NULL), len(DROP_REDUNDANT)]
    colors = [BLUE, "#a8a6a0", "#bcbab3", "#cfcdc6"]

    fig, ax = plt.subplots(figsize=(9, 3.2), dpi=200)
    y = range(len(cats))
    ax.barh(y, vals, color=colors, height=0.62, zorder=3)
    for i, v in enumerate(vals):
        ax.text(v + 0.6, i, f"{v} ({v/79*100:.0f}%)", va="center", ha="left",
                color=INK, fontsize=10, fontweight="bold")
    ax.set_yticks(list(y)); ax.set_yticklabels(cats, fontsize=10, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 37)
    ax.set_title("Column keep/drop decision: 79 to 31 columns",
                 fontsize=12.5, fontweight="bold", color=INK, pad=22, loc="left")
    ax.text(0, 1.08, "kept 31 · dropped 48 — of the 79 source columns",
            transform=ax.transAxes, fontsize=10, color=INK2)
    ax.set_xticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "columns_kept_dropped.png")
    fig.savefig(out, bbox_inches="tight", facecolor=SURFACE)
    print("saved", out)


def monthly_rates():
    m = pd.read_csv(FRED_CACHE, parse_dates=["observation_date"])
    m.columns = ["date", "rate"]
    m["ym"] = m["date"].dt.to_period("M")
    mon = m.groupby("ym")["rate"].mean().round(3)
    mon = mon[(mon.index >= pd.Period("2024-01")) & (mon.index <= pd.Period("2026-06"))]
    return mon


def fig_mortgage(mon):
    import matplotlib.dates as mdates

    x = [p.to_timestamp() for p in mon.index]
    yv = mon.values

    fig, ax = plt.subplots(figsize=(9, 3.6), dpi=200)
    ax.plot(x, yv, color=BLUE, linewidth=2, zorder=3)
    ax.scatter(x, yv, color=BLUE, s=14, zorder=4)
    ax.scatter(x[-1], yv[-1], color=BLUE, s=46, zorder=5)  # emphasize the endpoint

    # direct-label first, last, min, max (padding + placement avoid collisions)
    imin, imax = int(yv.argmin()), int(yv.argmax())
    for i, dy, ha in [(0, -15, "center"), (len(yv) - 1, 9, "right"),
                      (imin, -15, "center"), (imax, 8, "center")]:
        ax.annotate(f"{yv[i]:.2f}%", (x[i], yv[i]),
                    textcoords="offset points", xytext=(0, dy), ha=ha,
                    fontsize=9.5, fontweight="bold", color=INK)

    ax.set_ylim(5.85, 7.25)
    ax.set_xlim(x[0] - pd.Timedelta(days=20), x[-1] + pd.Timedelta(days=30))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_ylabel("30-yr fixed rate (%)", fontsize=9)
    ax.set_title("US 30-yr fixed mortgage rate — monthly avg, Jan 2024 — Jun 2026",
                 fontsize=12.5, fontweight="bold", color=INK, pad=12, loc="left")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(MUTED); ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(length=0, labelsize=9)
    fig.text(0.01, -0.02, "Source: FRED MORTGAGE30US, monthly mean of weekly values",
             fontsize=8, color=MUTED)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "mortgage_rate_30yr.png")
    fig.savefig(out, bbox_inches="tight", facecolor=SURFACE)
    print("saved", out)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    fig_columns()
    mon = monthly_rates()
    fig_mortgage(mon)
    # print the monthly table for the README
    print("\nMonthly 30yr fixed rate (%):")
    for p, v in mon.items():
        print(f"  {p}  {v:.2f}")
    print(f"\nrange: min {mon.min():.2f}% ({mon.idxmin()})  "
          f"max {mon.max():.2f}% ({mon.idxmax()})  "
          f"latest {mon.iloc[-1]:.2f}% ({mon.index[-1]})")


if __name__ == "__main__":
    main()
