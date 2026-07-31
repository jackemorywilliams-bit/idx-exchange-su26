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


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
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
