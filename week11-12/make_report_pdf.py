"""
Weeks 11-12 - Generate the 1-page Market Intelligence Report as a native PDF.

Typeset directly with reportlab (no browser, no print headers/footers): letter
page, four stat tiles, the handbook's five sections, two charts drawn as vector
graphics, methods footnote. Every number comes from the repo's pipeline scripts.

Run: python3 make_report_pdf.py   ->  market_intelligence_report.pdf
"""

import os

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_intelligence_report.pdf")

W, H = letter                      # 612 x 792 pt
M = 40                             # margin
CW = W - 2 * M                     # content width 532

INK = HexColor("#1b1b1b")
RED = HexColor("#7a2e2b")
TAN = HexColor("#c9b18c")
GRAY = HexColor("#555555")
LGRAY = HexColor("#777777")
TILE_BG = HexColor("#faf8f4")
TILE_BD = HexColor("#c9c2b6")
GREEN = HexColor("#1f6f43")

BODY = ParagraphStyle("body", fontName="Times-Roman", fontSize=9.3, leading=11.7,
                      textColor=INK, alignment=4)  # justified
BULLET = ParagraphStyle("bullet", parent=BODY, fontSize=8.9, leading=11.0,
                        leftIndent=10, bulletIndent=0)
FOOT = ParagraphStyle("foot", fontName="Times-Roman", fontSize=6.6, leading=8.2,
                      textColor=LGRAY, alignment=0)


def para(c, text, x, y, width, style=BODY):
    """Draw a rich-text paragraph with its top edge at y; return the new y."""
    p = Paragraph(text, style)
    w, h = p.wrapOn(c, width, 1000)
    p.drawOn(c, x, y - h)
    return y - h


def heading(c, text, x, y):
    c.setFont("Helvetica-Bold", 8.3)
    c.setFillColor(RED)
    c.drawString(x, y - 8, text.upper())
    c.setFillColor(INK)
    return y - 13


def tile(c, x, y, w, h, number, label_lines):
    c.setFillColor(TILE_BG)
    c.setStrokeColor(TILE_BD)
    c.rect(x, y, w, h, stroke=1, fill=1)
    c.setFillColor(INK)
    c.setFont("Times-Bold", 15)
    c.drawCentredString(x + w / 2, y + h - 21, number)
    c.setFont("Helvetica", 6.3)
    c.setFillColor(GRAY)
    for i, ln in enumerate(label_lines):
        c.drawCentredString(x + w / 2, y + h - 32 - i * 7.6, ln)
    c.setFillColor(INK)


def chart_supply(c, x, y, w, h):
    """Grouped bars: new listings vs closed sales by year. (x,y)=bottom-left."""
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(INK)
    c.drawCentredString(x + w / 2, y + h - 8, "New listings vs. closed sales, Jan–Jun of each year")
    base, top = y + 14, y + h - 30
    scale = (top - base) / 17691.0
    data = [("H1 2024", 14136, 13065, "14.1K", "13.1K"),
            ("H1 2025", 14396, 13053, "14.4K", "13.1K"),
            ("H1 2026", 17691, 13047, "17.7K", "13.0K")]
    bw, gap, group = 26, 4, (w - 30) / 3.0
    for i, (lab, l, s, ll, sl) in enumerate(data):
        gx = x + 18 + i * group + (group - (2 * bw + gap)) / 2
        lh, sh = l * scale, s * scale
        c.setFillColor(TAN)
        c.rect(gx, base, bw, lh, stroke=0, fill=1)
        c.setFillColor(RED)
        c.rect(gx + bw + gap, base, bw, sh, stroke=0, fill=1)
        c.setFont("Helvetica", 6.6)
        c.setFillColor(INK)
        c.drawCentredString(gx + bw / 2, base + lh + 3, ll)
        c.setFillColor(RED)
        c.drawCentredString(gx + bw + gap + bw / 2, base + sh + 3, sl)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 6.8)
        c.drawCentredString(gx + bw + gap / 2, y + 4, lab)
    c.setFont("Helvetica-Oblique", 6.2)
    c.setFillColor(GRAY)
    g0 = x + 18 + (group - (2 * 26 + 4)) / 2
    c.drawCentredString(g0 + 13, base + 14136 * scale + 11, "listings")
    c.setFillColor(HexColor("#ffffff"))
    c.drawCentredString(g0 + 43, base + 13065 * scale - 9, "sold")
    gx2 = x + 18 + 2 * group + (group - (2 * 26 + 4)) / 2
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 7)
    c.drawRightString(gx2 - 5, base + 16600 * scale, "+23% supply, flat sales →")
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.line(x + 6, base - 1, x + w - 6, base - 1)
    c.setFillColor(INK)


def chart_offices(c, x, y, w, h):
    """Horizontal bars: top Riverside offices, 2026 H1. (x,y)=bottom-left."""
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(INK)
    c.drawCentredString(x + w / 2, y + h - 8, "Closed sides, 2026 H1 — top offices")
    rows = [("Equity Union", 473, RED), ("Coldwell Banker Realty", 457, TAN),
            ("Compass", 453, TAN), ("Bennion Deville Homes", 390, TAN),
            ("Century 21 Masters", 322, TAN)]
    label_w, val_w = 96, 22
    bar_max = w - label_w - val_w - 14
    row_h = (h - 30) / 5.0
    for i, (name, v, col) in enumerate(rows):
        ry = y + h - 22 - (i + 1) * row_h + (row_h - 9) / 2
        c.setFont("Helvetica", 6.8)
        c.setFillColor(INK)
        c.drawRightString(x + label_w, ry + 2, name)
        c.setFillColor(col)
        bl = bar_max * v / 473.0
        c.rect(x + label_w + 4, ry, bl, 9, stroke=0, fill=1)
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 6.8)
        c.setFillColor(INK)
        c.drawString(x + label_w + 8 + bl, ry + 2, str(v))
    c.setFont("Helvetica-Oblique", 6.2)
    c.setFillColor(GRAY)
    c.drawCentredString(x + w / 2, y + 2, "a 20-side race for #1")
    c.setFillColor(INK)


def main():
    c = canvas.Canvas(OUT, pagesize=letter)
    c.setTitle("Riverside County Market Intelligence - Emory Williams")

    y = H - M - 4
    c.setFont("Times-Bold", 19)
    c.drawString(M, y - 14, "Riverside County Market Intelligence")
    y -= 20
    c.setFont("Times-Italic", 10.3)
    c.drawString(M, y - 10, "CRMLS residential, January 2024 – June 2026 — "
                            "prices froze; the competitive order didn’t.")
    y -= 14
    c.setFont("Helvetica", 6.9)
    c.setFillColor(GRAY)
    c.drawString(M, y - 8, "EMORY WILLIAMS  ·  IDX EXCHANGE DATA ANALYST INTERNSHIP  ·  SUMMER 2026")
    c.setFillColor(INK)
    y -= 13
    c.setLineWidth(2.2)
    c.setStrokeColor(INK)
    c.line(M, y, W - M, y)
    y -= 8

    tw, th, tg = (CW - 3 * 8) / 4.0, 46, 8
    labels = [("$600K", ["median close price — unchanged", "2024, 2025, and 2026 H1"]),
              ("$321", ["median price per sq ft —", "unchanged all three years"]),
              ("34 days", ["days on market, 2026 H1 — IQR-", "filtered avg (31 in 2024)"]),
              ("98.0%", ["sale-to-ask, 2026 H1 — IQR-", "filtered avg (98.6% in 2024)"])]
    for i, (n, ls) in enumerate(labels):
        tile(c, M + i * (tw + tg), y - th, tw, th, n, ls)
    y -= th + 10

    y = heading(c, "Market Overview", M, y)
    y = para(c, "Riverside’s price level has not moved in thirty months — the change is in "
                "how long selling takes. The median closed at exactly <b>$600,000</b> in 2024, in 2025, "
                "and again through June 2026, corroborated by a per-square-foot median likewise frozen at "
                "<b>$321</b>, which makes a mix-shift artifact unlikely. Nor is it clustering at a headline "
                "number: only 1.1% of closings land exactly at $600,000 and 3.1% within $5,000 of it, so the "
                "frozen median reflects a stable price distribution. What drifted is pace — average days on "
                "market rose from 31 to 34, about 10% slower.", M, y, CW)
    y -= 7

    y = heading(c, "Pricing Trends", M, y)
    y = para(c, "Sellers are conceding at the margin, not on price. The sale-to-ask ratio slipped from "
                "0.986 to 0.980 — under one point, but every year of the window closed below asking. "
                "Negotiation, not repricing, is the only pricing dial that has moved.", M, y, CW)
    y -= 8

    col_w = (CW - 22) / 2.0
    lx, rx = M, M + col_w + 22
    ly = heading(c, "Market Activity", lx, y)
    ly = para(c, "Comparing like halves of the year, 2026 is the first time supply pulled away from "
                 "sales: January–June listings ran 14,136 → 14,396 → <b><font color='#1f6f43'>17,691 "
                 "(+23%)</font></b>, while January–June sales were 13,065 → 13,053 → 13,047 — flat to "
                 "within 18 transactions. New listings per closed sale: <b>1.08 → 1.10 → 1.36</b>.",
              lx, ly, col_w)
    chart_supply(c, lx, ly - 158, col_w, 152)

    ry = heading(c, "Competitive Landscape", rx, y)
    ry = para(c, "While volume froze, the leaderboard reshuffled. A regional independent — Equity "
                 "Union — now runs the county’s <b>#1 office</b> by closed listing sides, in a "
                 "20-side dead heat with Coldwell Banker Realty and Compass. At brand level, Coldwell "
                 "Banker remains largest and growing (<b>6.3→7.0%</b> of listing sides), Century 21 "
                 "<b>3.4→4.4%</b>, Compass <b>3.1→3.9%</b>; Keller Williams slipped "
                 "<b>5.5→4.9%</b> and Opendoor wound down <b>0.8→0.2%</b>. It mirrors California "
                 "at large: Compass leads the state at $23.7B of 2024 volume, insurgent brands are doubling "
                 "their affordable-tier share — and only 21 of 500 (then 16 of 495) top producers "
                 "changed brands, so the race is being won through listing acquisition, not agent "
                 "movement (statewide figures computed from the same extract; see footnote).",
              rx, ry, col_w)
    chart_offices(c, rx, ry - 120, col_w, 114)

    y = min(ly - 158, ry - 120) - 14

    y = heading(c, "Key Takeaways", M, y)
    takeaways = [
        "<b>Prices haven’t moved:</b> median $600,000 and $321/sq ft are flat across 2024–2026, "
        "while days on market drifted from 31 to 34.",
        "<b>Supply is pulling ahead:</b> like-for-like, Jan–Jun listings jumped 14.1K → 14.4K → 17.7K (+23%) "
        "while Jan–Jun sales stayed flat within 18 transactions (1.08 → 1.10 → 1.36 listings per sale).",
        "<b>The top is a dead heat:</b> Equity Union (473 sides) leads Coldwell Banker Realty (457) and "
        "Compass (453) by under 5% in 2026 H1.",
        "<b>Share shifted even as volume froze:</b> Coldwell 6.3→7.0%, Century 21 3.4→4.4%, "
        "Compass 3.1→3.9%; Keller Williams 5.5→4.9%, Opendoor 0.8→0.2%.",
        "<b>What to watch:</b> if H2 2026 sustains the H1 supply gap, the first crack in the $600K median "
        "should appear in sale-to-ask before it appears in price.",
    ]
    for t in takeaways:
        y = para(c, "•&nbsp;&nbsp;" + t, M + 2, y, CW - 4, BULLET) - 2

    fy = M + 26
    c.setStrokeColor(TILE_BD)
    c.setLineWidth(0.7)
    c.line(M, fy, W - M, fy)
    para(c, "CRMLS closed residential sales, Riverside County, Jan 2024 – Jun 2026. Supply–sales "
            "comparisons are Jan–Jun of each year (like-for-like; no annualization anywhere). 255 placeholder "
            "records excluded from rankings; sale-to-ask guarded to (0,2]; DOM and sale-to-ask tiles are "
            "IQR-filtered averages, price tiles are all-rows medians. Statewide figures (Compass volume, "
            "producer-switch counts, tier shares) are computed from the same statewide CRMLS extract with the "
            "same rules — no external sources. Dashboards: public.tableau.com/app/profile/emory.williams · "
            "Code: github.com/jackemorywilliams-bit/idx-exchange-su26", M, fy - 4, CW, FOOT)

    c.showPage()
    c.save()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
