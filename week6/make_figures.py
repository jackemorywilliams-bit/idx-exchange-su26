"""
Generate the Week 6 README figure: school-district match coverage for both
datasets as 100%-stacked bars (matched / no unified district / missing coords /
invalid coords), with direct labels. Counts come from the feature_engineering
RUN LOG. Colors follow the data-viz reference palette on a light surface.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")

SURFACE = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"
BLUE = "#2a78d6"; YELLOW = "#eda100"; GREY = "#bcbab3"; DARKGREY = "#6b6963"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2,
    "ytick.color": INK2, "axes.edgecolor": MUTED,
})

# (label, matched, no_unified, missing_coords, invalid) -- from the RUN LOG
DATA = [
    ("Sold\n455,449 rows", 307_683, 94_032, 53_625, 109),
    ("Listings\n504,162 rows", 348_301, 106_190, 49_455, 216),
]
SEGMENTS = ["Matched to a unified district", "No unified district (expected geography)",
            "Missing coordinates (known gap)", "Invalid coordinates"]
COLORS = [BLUE, GREY, YELLOW, DARKGREY]


def fig_new_column_findings():
    """2x2 panel: what the engineered columns reveal (medians from the run)."""
    fig, axes = plt.subplots(2, 2, figsize=(9, 6.2), dpi=200)
    fig.suptitle("What the new Week 6 columns show — sold homes, Jan 2024 – Jun 2026",
                 fontsize=12.5, fontweight="bold", color=INK, x=0.02, ha="left")

    # (a) price_ratio: sale vs original asking price
    ax = axes[0][0]
    segs = [("Above ask", 36.9, BLUE), ("At ask", 11.7, GREY), ("Below ask", 51.3, "#e34948")]
    left = 0
    for name, v, c in segs:
        ax.barh(0, v, left=left, color=c, height=0.5, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.text(left + v / 2, 0.45, f"{name}\n{v:.0f}%", ha="center", fontsize=8.5,
                color=INK, fontweight="bold")
        left += v
    ax.set_xlim(0, 100); ax.set_ylim(-0.6, 1.0)
    ax.set_title("Sale price vs original ask (price_ratio)\nmedian home closes at 99.5% of ask",
                 fontsize=10, fontweight="bold", loc="left", color=INK)
    ax.axis("off")

    # (b) anatomy of a sale: the two duration columns
    ax = axes[0][1]
    ax.barh(0, 25, color=BLUE, height=0.5, zorder=3, edgecolor=SURFACE, linewidth=2)
    ax.barh(0, 29, left=25, color="#1baf7a", height=0.5, zorder=3,
            edgecolor=SURFACE, linewidth=2)
    ax.text(12.5, 0.45, "Listed to offer\n25 days", ha="center", fontsize=8.5,
            color=INK, fontweight="bold")
    ax.text(39.5, 0.45, "Offer to keys\n29 days", ha="center", fontsize=8.5,
            color=INK, fontweight="bold")
    ax.text(54.8, 0, "= 54 days\ndoor to door", va="center", fontsize=9,
            color=INK, fontweight="bold")
    ax.set_xlim(0, 72); ax.set_ylim(-0.6, 1.0)
    ax.set_title("Anatomy of a typical sale (median days)\nlisting_to_contract + contract_to_close",
                 fontsize=10, fontweight="bold", loc="left", color=INK)
    ax.axis("off")

    # (c) price_per_sqft by county
    ax = axes[1][0]
    counties = [("San Mateo", 1036), ("Santa Clara", 945), ("Orange", 673),
                ("Los Angeles", 608), ("San Diego", 589), ("San Bernardino", 332),
                ("Riverside", 321)]
    y = range(len(counties))
    ax.barh(y, [v for _, v in counties], color=BLUE, height=0.6, zorder=3)
    for i, (name, v) in enumerate(counties):
        ax.text(v + 15, i, f"${v:,}", va="center", fontsize=8.5, color=INK,
                fontweight="bold")
    ax.set_yticks(list(y)); ax.set_yticklabels([n for n, _ in counties], fontsize=9)
    ax.invert_yaxis(); ax.set_xlim(0, 1250); ax.set_xticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("Median price per sqft by county (price_per_sqft)\ncoast costs 3× the Inland Empire",
                 fontsize=10, fontweight="bold", loc="left", color=INK)

    # (d) median price_ratio by county, deviation from 1.0 (= asking price)
    ax = axes[1][1]
    ratios = [("Santa Clara", 1.018), ("San Mateo", 1.011), ("Los Angeles", 1.000),
              ("Orange", 0.994), ("San Diego", 0.992), ("San Bernardino", 0.992),
              ("Riverside", 0.986)]
    y = range(len(ratios))
    vals = [(r - 1) * 100 for _, r in ratios]
    ax.barh(y, vals, color=[BLUE if v > 0 else "#e34948" for v in vals],
            height=0.6, zorder=3)
    for i, ((name, r), v) in enumerate(zip(ratios, vals)):
        ax.text(v + (0.1 if v >= 0 else -0.1), i, f"{r:.3f}",
                va="center", ha="left" if v >= 0 else "right",
                fontsize=8.5, color=INK, fontweight="bold")
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks(list(y)); ax.set_yticklabels([n for n, _ in ratios], fontsize=9)
    ax.invert_yaxis(); ax.set_xlim(-2.6, 2.9); ax.set_xticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("Median sale-to-ask ratio by county\nBay Area closes above ask; Inland Empire below",
                 fontsize=10, fontweight="bold", loc="left", color=INK)

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    out = os.path.join(FIG_DIR, "new_column_findings.png")
    fig.savefig(out, bbox_inches="tight", facecolor=SURFACE)
    print("saved", out)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    fig_new_column_findings()
    fig, ax = plt.subplots(figsize=(9, 2.9), dpi=200)

    for row, (label, *vals) in enumerate(DATA):
        total = sum(vals)
        left = 0.0
        for seg_i, v in enumerate(vals):
            w = v / total * 100
            ax.barh(row, w, left=left, color=COLORS[seg_i], height=0.58,
                    zorder=3, edgecolor=SURFACE, linewidth=2)
            if w > 6:  # direct-label the segments wide enough to hold text
                ax.text(left + w / 2, row, f"{v:,}\n{w:.1f}%", va="center",
                        ha="center", fontsize=9, fontweight="bold",
                        color="#ffffff" if seg_i == 0 else INK)
            left += w

    ax.set_yticks(range(len(DATA)))
    ax.set_yticklabels([d[0] for d in DATA], fontsize=10, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)

    ax.set_title("School-district match coverage — share of rows",
                 fontsize=12.5, fontweight="bold", color=INK, pad=30, loc="left")
    ax.text(0, 1.16, "Unified districts only; unmatched valid points sit in "
                     "elementary/high-district territory by design",
            transform=ax.transAxes, fontsize=10, color=INK2)

    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COLORS]
    ax.legend(handles, SEGMENTS, loc="upper center", bbox_to_anchor=(0.5, -0.06),
              ncol=2, frameon=False, fontsize=9)

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "district_match_coverage.png")
    fig.savefig(out, bbox_inches="tight", facecolor=SURFACE)
    print("saved", out)


if __name__ == "__main__":
    main()
