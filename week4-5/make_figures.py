"""
Generate the Weeks 4-5 README figure: prevalence of each data-quality flag on the
cleaned SOLD dataset, colored by flag family, on a log x-axis (missing-coordinates
dwarfs every other issue, so a linear axis would hide the rest).
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
FLAGGED = os.path.expanduser(
    "~/idx-exchange/deliverables/Week 4-5 _ Deliverable _ Sold Residential Cleaned Flagged.csv")

SURFACE = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"; GRID = "#e1e0d9"
BLUE = "#2a78d6"; AQUA = "#1baf7a"; YELLOW = "#eda100"; ORANGE = "#eb6834"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "text.color": INK,
    "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2, "axes.edgecolor": MUTED,
})

# flag -> (pretty label, family)
FAMILY = {
    "invalid_livingarea_flag": ("LivingArea <= 0", "numeric-invalid"),
    "negative_dom_flag": ("DaysOnMarket < 0", "numeric-invalid"),
    "invalid_closeprice_flag": ("ClosePrice <= 0", "numeric-invalid"),
    "negative_beds_flag": ("Bedrooms < 0", "numeric-invalid"),
    "negative_baths_flag": ("Bathrooms < 0", "numeric-invalid"),
    "listing_after_close_flag": ("Listing date > close", "date-consistency"),
    "purchase_after_close_flag": ("Purchase date > close", "date-consistency"),
    "negative_timeline_flag": ("Timeline out of order", "date-consistency"),
    "missing_coords_flag": ("Missing coordinates", "geographic"),
    "zero_coord_flag": ("Zero-sentinel coord", "geographic"),
    "positive_longitude_flag": ("Longitude > 0 (sign)", "geographic"),
    "out_of_ca_flag": ("Outside CA box", "geographic"),
    "suspicious_low_price_flag": ("Price < $10k", "review-outlier"),
    "extreme_high_price_flag": ("Price > $100M", "review-outlier"),
    "extreme_livingarea_flag": ("LivingArea > 25k sqft", "review-outlier"),
    "implausible_yearbuilt_flag": ("YearBuilt implausible", "review-outlier"),
}
FAM_COLOR = {"numeric-invalid": ORANGE, "date-consistency": YELLOW,
             "geographic": AQUA, "review-outlier": BLUE}


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    df = pd.read_csv(FLAGGED, usecols=list(FAMILY), low_memory=False)
    counts = {f: int(df[f].sum()) for f in FAMILY}
    items = [(FAMILY[f][0], counts[f], FAMILY[f][1]) for f in FAMILY if counts[f] > 0]
    items.sort(key=lambda t: t[1])

    labels = [t[0] for t in items]
    vals = [t[1] for t in items]
    colors = [FAM_COLOR[t[2]] for t in items]

    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=200)
    y = range(len(items))
    ax.barh(y, vals, color=colors, height=0.66, zorder=3)
    for i, v in enumerate(vals):
        ax.text(v * 1.12, i, f"{v:,}", va="center", ha="left", color=INK,
                fontsize=9.5, fontweight="bold")
    ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=9.5, color=INK)
    ax.set_xscale("log")
    ax.set_xlim(1, 200_000)
    ax.set_xlabel("rows flagged (log scale) — of 455,658 sold rows", fontsize=9)
    ax.set_title("Weeks 4-5 data-quality flags — sold dataset\n"
                 "missing coordinates dominate; every other issue is < 0.1%",
                 fontsize=12.5, fontweight="bold", color=INK, pad=10, loc="left")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    legend = [mpatches.Patch(color=FAM_COLOR[k], label=k) for k in FAM_COLOR]
    ax.legend(handles=legend, loc="lower right", frameon=False, fontsize=9,
              title="flag family", title_fontsize=9)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "data_quality_flags.png")
    fig.savefig(out, bbox_inches="tight", facecolor=SURFACE)
    print("saved", out)


if __name__ == "__main__":
    main()
