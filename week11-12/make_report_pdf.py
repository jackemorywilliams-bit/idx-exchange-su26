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

BODY = ParagraphStyle("body", fontName="Times-Roman", fontSize=9.0, leading=11.2,
                      textColor=INK, alignment=4)  # justified
BULLET = ParagraphStyle("bullet", parent=BODY, fontSize=8.7, leading=10.4,
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

    tw, th, tg = (CW - 3 * 8) / 4.0, 44, 8
    labels = [("$600K", ["median close price — unchanged", "2024, 2025, and 2026 H1"]),
              ("$321", ["median price per sq ft —", "unchanged all three years"]),
              ("34 days", ["days on market, 2026 H1 — IQR-", "filtered avg (31 in 2024)"]),
              ("98.0%", ["sale-to-ask, 2026 H1 — IQR-", "filtered avg (98.6% in 2024)"])]
    for i, (n, ls) in enumerate(labels):
        tile(c, M + i * (tw + tg), y - th, tw, th, n, ls)
    y -= th + 8
    y = para(c, "<i>This report tracks two things: what homes cost in Riverside County, and which companies "
                "sell them. The short version — prices have not moved in two and a half years, but the "
                "competition among the companies selling those homes has changed hands.</i>", M, y, CW)
    y -= 6

    y = heading(c, "Market Overview", M, y)
    y = para(c, "The median sale — the middle home, half sold for more and half for less — closed at "
                "exactly <b>$600,000</b> in 2024, in 2025, and again through June 2026. Price per square "
                "foot, which corrects for the size of homes sold, is likewise frozen at <b>$321</b> — so this "
                "is not an illusion created by bigger or smaller homes changing hands (fewer than 2% of sales "
                "land exactly at $600,000, so it is a market-wide plateau, not a quirk of round numbers). "
                "What did change is speed: the typical home now takes <b>34 days</b> to sell, up from 31 — "
                "about 10% slower.", M, y, CW)
    y -= 5

    y = heading(c, "Pricing Trends", M, y)
    y = para(c, "The sale-to-ask ratio compares what a home sold for against what the seller asked. At "
                "today’s <b>98.0%</b>, buyers pay about $98,000 for every $100,000 of asking price — down "
                "from $98,600 in 2024. Sellers are not cutting their asking prices; they are giving a little "
                "more ground in negotiation. That is the only pricing dial that has moved.", M, y, CW)
    y -= 6

    col_w = (CW - 22) / 2.0
    lx, rx = M, M + col_w + 22
    ly = heading(c, "Market Activity", lx, y)
    ly = para(c, "Comparing the same six months of each year: the number of homes <i>put up for sale</i> "
                 "jumped from about 14,100 to <b><font color='#1f6f43'>17,691 (+23%)</font></b> in early "
                 "2026, while the number that actually <i>sold</i> stayed flat — 13,065, 13,053, then "
                 "13,047. More homes are coming to market than are selling, so unsold homes are piling up "
                 "and buyers have more to choose from — the classic setup for price pressure later.",
              lx, ly, col_w)
    chart_supply(c, lx, ly - 142, col_w, 136)

    ry = heading(c, "Competitive Landscape", rx, y)
    ry = para(c, "Every sale credits one office as the seller’s representative — a “listing side,” "
                 "the scoreboard of this business. By that score, a Southern California independent, "
                 "<b>Equity Union</b>, now runs the county’s <b>#1 office</b>, twenty sides ahead of "
                 "national names Coldwell Banker Realty and Compass. Among brands (one brand operates many "
                 "offices), Coldwell Banker grew from 6.3% to <b>7.0%</b> of sides, Century 21 to "
                 "<b>4.4%</b>, Compass to <b>3.9%</b>; Keller Williams slipped to <b>4.9%</b>. "
                 "<b>Opendoor</b> — the tech “iBuyer” that bought homes for cash and resold them — has "
                 "nearly left: 0.8% of listings down to <b>0.2%</b>; statewide, buy-to-resell investor "
                 "flips are just 4.7% of sales. The same pattern holds across California: Compass leads the "
                 "state at $23.7B of 2024 volume, low-fee newcomers are doubling their share in affordable "
                 "areas, and almost no top agents switch firms (21 of 500 one year, 16 of 495 the next) — "
                 "companies win by attracting home sellers, not by hiring away star agents (statewide "
                 "figures from the same data; see footnote).", rx, ry, col_w)
    chart_offices(c, rx, ry - 110, col_w, 104)

    y = min(ly - 142, ry - 110) - 12

    y = heading(c, "Key Takeaways", M, y)
    takeaways = [
        "<b>The price of a Riverside home hasn’t moved in 2½ years</b> — $600,000 median, $321 per "
        "square foot — but each sale takes a few days longer than it used to.",
        "<b>More sellers, same number of buyers:</b> homes listed for sale jumped 23% in early 2026 while "
        "purchases stayed flat — inventory is building, which favors buyers.",
        "<b>Who sells Riverside changed:</b> a local independent, Equity Union, now edges out the national "
        "brands — #1 by a margin of just 20 sales over Coldwell Banker Realty and Compass.",
        "<b>The cash-offer experiment ended here:</b> Opendoor, the app that bought homes directly, fell "
        "from 0.8% to 0.2% of listings; traditional agents kept the market.",
        "<b>What to watch:</b> if supply keeps outrunning sales, expect buyers to win bigger discounts "
        "first (the sale-to-ask ratio), and asking prices to bend only after that.",
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
