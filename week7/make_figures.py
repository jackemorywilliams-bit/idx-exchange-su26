"""
Week 7 README figures (numbers from the RUN LOG / observed output):
  1. iqr_mean_vs_median.png -- slope chart: the mean collapses under IQR
     filtering while the median barely moves (the week's lesson).
  2. iqr_flag_rates.png -- grouped bars: share of rows above each fence,
     sold vs listings (NOT stacked: the three fences overlap, so they do
     not sum to the "any" rate).
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")

SURFACE = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"
BLUE = "#2a78d6"; AQUA = "#1baf7a"; RED = "#e34948"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2,
    "ytick.color": INK2, "axes.edgecolor": MUTED,
})


def fig_mean_vs_median():
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=200)
    x = [0, 1]
    mean_y = [1_123_321, 887_946]
    med_y = [815_000, 780_000]

    for ys, c in [(mean_y, RED), (med_y, BLUE)]:
        ax.plot(x, ys, color=c, linewidth=2.5, marker="o", markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)

    ax.text(-0.06, mean_y[0], "Mean  $1,123,321", ha="right", va="center",
            fontsize=9.5, fontweight="bold", color=INK)
    ax.text(-0.06, med_y[0], "Median  $815,000", ha="right", va="center",
            fontsize=9.5, fontweight="bold", color=INK)
    ax.text(1.06, mean_y[1], "$887,946   −21%", ha="left", va="center",
            fontsize=9.5, fontweight="bold", color=INK)
    ax.text(1.06, med_y[1], "$780,000   −4.3%", ha="left", va="center",
            fontsize=9.5, fontweight="bold", color=INK)

    ax.set_xlim(-0.75, 1.75); ax.set_ylim(700_000, 1_200_000)
    ax.set_xticks(x)
    ax.set_xticklabels(["All sold rows\n455,449", "IQR-filtered\n385,003"],
                       fontsize=10, color=INK)
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    fig.suptitle("The average was the outlier problem — the median barely moves",
                 fontsize=12.5, fontweight="bold", color=INK, x=0.02, y=0.985,
                 ha="left")
    fig.text(0.02, 0.905, "Sold ClosePrice before vs after IQR filtering — a handful "
                          "of \\$10M+ sales inflated the mean by ~\\$235K; "
                          "listings behave the same",
             fontsize=10, color=INK2)
    fig.subplots_adjust(top=0.82, bottom=0.12, left=0.06, right=0.97)
    out = os.path.join(FIG_DIR, "iqr_mean_vs_median.png")
    fig.savefig(out, bbox_inches="tight", facecolor=SURFACE)
    print("saved", out)


def fig_flag_rates():
    cats = ["ClosePrice > $2,342,150", "LivingArea > 3,680 sqft",
            "Days on market > 110", "Any fence — row dropped"]
    sold = [7.41, 4.36, 7.46, 15.47]
    lst = [6.04, 4.54, 7.70, 15.21]
    # extra half-unit gap before the "Any" row
    ys = [0, 1, 2, 3.5]

    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=200)
    for i, y in enumerate(ys):
        ax.barh(y - 0.21, sold[i], color=BLUE, height=0.36, zorder=3)
        ax.barh(y + 0.21, lst[i], color=AQUA, height=0.36, zorder=3)
        s_lbl = f"{sold[i]:.2f}%" + ("  (70,446 rows)" if i == 3 else "")
        l_lbl = f"{lst[i]:.2f}%" + ("  (76,694 rows)" if i == 3 else "")
        ax.text(sold[i] + 0.25, y - 0.21, s_lbl, va="center", fontsize=9,
                fontweight="bold", color=INK)
        ax.text(lst[i] + 0.25, y + 0.21, l_lbl, va="center", fontsize=9,
                fontweight="bold", color=INK)

    ax.set_yticks(ys); ax.set_yticklabels(cats, fontsize=10, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 19.5); ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    handles = [plt.Rectangle((0, 0), 1, 1, color=BLUE),
               plt.Rectangle((0, 0), 1, 1, color=AQUA)]
    ax.legend(handles, ["Sold", "Listings"], frameon=False, fontsize=9.5,
              loc="center right", bbox_to_anchor=(1.0, 0.85))
    fig.suptitle("About one row in six trips an IQR fence — sold and listings agree",
                 fontsize=12.5, fontweight="bold", color=INK, x=0.02, y=0.985,
                 ha="left")
    fig.text(0.02, 0.905, "Share of rows above each upper fence; filtered files keep "
                          "385,003 of 455,449 sold and 427,468 of 504,162 listing rows",
             fontsize=10, color=INK2)
    fig.subplots_adjust(top=0.84, bottom=0.06, left=0.24, right=0.97)
    out = os.path.join(FIG_DIR, "iqr_flag_rates.png")
    fig.savefig(out, bbox_inches="tight", facecolor=SURFACE)
    print("saved", out)


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    fig_mean_vs_median()
    fig_flag_rates()


if __name__ == "__main__":
    main()
