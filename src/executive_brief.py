"""
executive_brief.py
------------------
Generates a 2-page executive brief PDF for the Conut AI Chief of Operations system.
Covers all 5 business objectives with key findings, recommendations, impact and risks.

Usage:
    python src/executive_brief.py
    -> outputs: executive_brief.pdf
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpdf import FPDF, XPos, YPos
from fpdf.enums import TableCellFillMode


# ---------------------------------------------------------------------------
# Colour palette (Conut brand-adjacent)
# ---------------------------------------------------------------------------
DARK_BG    = (26,  26,  46)   # deep navy
ACCENT     = (230, 100,  30)  # warm orange
LIGHT_GREY = (245, 245, 245)
MID_GREY   = (180, 180, 180)
WHITE      = (255, 255, 255)
TEXT_DARK  = (30,  30,  30)
TEXT_MID   = (80,  80,  80)
GREEN      = (34, 139,  34)
RED        = (200,  50,  50)
BLUE       = (30,  80, 180)


def _s(text: str) -> str:
    """Sanitize text to latin-1 safe ASCII by replacing common unicode chars."""
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2012": "-", "\u2011": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2022": "*", "\u2023": ">", "\u2192": "->", "\u2190": "<-",
        "\u2713": "OK", "\u2717": "X", "\u00d7": "x", "\u00f7": "/",
        "\u2264": "<=", "\u2265": ">=", "\u2248": "~=", "\u221e": "inf",
        "\u221a": "sqrt", "\u03b1": "a", "\u03b2": "b",
        "\u00e9": "e", "\u00e8": "e", "\u00ea": "e", "\u00eb": "e",
        "\u00e0": "a", "\u00e2": "a", "\u00e4": "a",
        "\u00f9": "u", "\u00fb": "u", "\u00fc": "u",
        "\u00ee": "i", "\u00ef": "i",
        "\u00f4": "o", "\u00f6": "o",
        "\u00e7": "c", "\u00c7": "C",
        "\u2026": "...",
        "\u00b0": " deg", "\u00b2": "^2", "\u00b3": "^3",
        "\u00a0": " ",  # non-breaking space
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Final fallback: drop anything outside latin-1
    return text.encode("latin-1", errors="replace").decode("latin-1")


class BriefPDF(FPDF):
    """Custom FPDF subclass with brand header/footer."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=18)
        self.add_page()

    # ------------------------------------------------------------------
    # Header / Footer
    # ------------------------------------------------------------------
    def header(self):
        # Dark banner
        self.set_fill_color(*DARK_BG)
        self.rect(0, 0, 210, 16, "F")
        # Logo text left
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*ACCENT)
        self.set_xy(10, 4)
        self.cell(80, 8, _s("CONUT AI CHIEF OF OPERATIONS"), new_x=XPos.RIGHT, new_y=YPos.TOP)
        # Right: team tag
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MID_GREY)
        self.set_xy(130, 5)
        self.cell(70, 6, _s("Team 503  |  AI Engineering Hackathon  |  Feb 2026"),
                  align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*MID_GREY)
        self.set_fill_color(*DARK_BG)
        self.rect(0, 285, 210, 12, "F")
        self.set_text_color(*MID_GREY)
        self.set_xy(10, 286)
        self.cell(90, 6, _s("CONFIDENTIAL - Hackathon Submission"), new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_xy(110, 286)
        self.cell(90, 6, _s(f"Page {self.page_no()} of 2"), align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def section_title(self, number: str, title: str):
        """Orange-accented section heading."""
        self.ln(3)
        self.set_fill_color(*ACCENT)
        self.rect(self.get_x(), self.get_y(), 4, 7, "F")
        self.set_x(self.get_x() + 6)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK_BG)
        self.cell(0, 7, _s(f"{number}  {title.upper()}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def kpi_row(self, items: list[tuple[str, str, tuple]]):
        """Row of KPI boxes: [(label, value, value_colour), ...]."""
        box_w = (self.epw) / len(items)
        start_x = self.l_margin
        y = self.get_y()
        for label, value, col in items:
            self.set_fill_color(*LIGHT_GREY)
            self.rect(start_x, y, box_w - 2, 16, "F")
            self.set_xy(start_x + 2, y + 1)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*TEXT_MID)
            self.cell(box_w - 4, 5, _s(label.upper()), new_x=XPos.LEFT, new_y=YPos.NEXT)
            self.set_xy(start_x + 2, y + 6)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*col)
            self.cell(box_w - 4, 8, _s(value), new_x=XPos.LEFT, new_y=YPos.NEXT)
            start_x += box_w
        self.set_y(y + 18)

    def two_col_table(self, headers: list[str], rows: list[list[str]],
                      col_widths: list[float] | None = None):
        """Simple table with alternating row shading."""
        epw = self.epw
        if col_widths is None:
            col_widths = [epw / len(headers)] * len(headers)

        # Header row
        self.set_fill_color(*DARK_BG)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 7.5)
        for i, (h, w) in enumerate(zip(headers, col_widths)):
            self.cell(w, 6, _s(h), border=0, fill=True,
                      new_x=XPos.RIGHT if i < len(headers) - 1 else XPos.LMARGIN,
                      new_y=YPos.TOP if i < len(headers) - 1 else YPos.NEXT)

        # Data rows
        self.set_font("Helvetica", "", 7.5)
        for r_idx, row in enumerate(rows):
            fill = r_idx % 2 == 0
            self.set_fill_color(*LIGHT_GREY if fill else WHITE)
            self.set_text_color(*TEXT_DARK)
            for i, (cell, w) in enumerate(zip(row, col_widths)):
                self.cell(w, 5.5, _s(str(cell)), border=0, fill=fill,
                          new_x=XPos.RIGHT if i < len(row) - 1 else XPos.LMARGIN,
                          new_y=YPos.TOP if i < len(row) - 1 else YPos.NEXT)
        self.ln(2)

    def bullet(self, text: str, colour: tuple = TEXT_DARK, indent: float = 5):
        self.set_x(self.l_margin + indent)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*colour)
        self.cell(4, 5, chr(149), new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.multi_cell(self.epw - indent - 4, 5, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def small_text(self, text: str, italic: bool = False, colour: tuple = TEXT_MID):
        style = "I" if italic else ""
        self.set_font("Helvetica", style, 7.5)
        self.set_text_color(*colour)
        self.multi_cell(self.epw, 5, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def divider(self):
        self.set_draw_color(*MID_GREY)
        self.line(self.l_margin, self.get_y(), self.l_margin + self.epw, self.get_y())
        self.ln(2)


# ---------------------------------------------------------------------------
# Page 1 — Problem framing + Objectives 1 & 2
# ---------------------------------------------------------------------------
def build_page1(pdf: BriefPDF):
    # ── Hero title ──────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*DARK_BG)
    pdf.cell(0, 10, _s("Executive Brief"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*TEXT_MID)
    pdf.cell(0, 6, _s("AI-Driven Operations for Conut Cafe Chain  |  5 Business Objectives  |  Feb 2026"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.divider()

    # ── Problem framing ─────────────────────────────────────────────────────
    pdf.section_title("0", "Problem Framing")
    pdf.small_text(
        "Conut operates 4 café branches with heterogeneous performance profiles. Leadership needs a single "
        "AI-powered system that (1) decides when and where to expand, (2) right-sizes staffing, "
        "(3) maximises basket size through intelligent combos, (4) forecasts demand to align inventory, "
        "and (5) unlocks untapped beverage revenue. This brief summarises findings across all five workstreams."
    )
    pdf.ln(1)

    # ── Top-line KPIs ───────────────────────────────────────────────────────
    pdf.kpi_row([
        ("Expansion Decision", "GO - High", GREEN),
        ("Anomalies Detected", "9 Shifts", RED),
        ("MBA Rules Found", "35 Rules", BLUE),
        ("Network Jan-26", "9.47 B", ACCENT),
        ("Bev. Revenue", "1.36 B", BLUE),
    ])

    # ── Objective 1 ─────────────────────────────────────────────────────────
    pdf.section_title("1", "Branch Expansion Intelligence")
    pdf.two_col_table(
        ["Branch", "Score /100", "MoM Growth", "Momentum", "Verdict"],
        [
            ["Main Street Coffee", "100", "+176.2 %", "4.12x", "GO - TEMPLATE"],
            ["Conut Jnah",         "91",  "+67.7 %",  "4.10x", "GO - Strong"],
            ["Conut - Tyre",       "49",  "+21.0 %",  "0.99x", "Watch"],
            ["Conut (original)",   "0",   "-40.8 %",  "0.07x", "DECLINING"],
        ],
        col_widths=[55, 25, 28, 24, 28],
    )
    pdf.bullet("RECOMMENDATION: Open 5th branch replicating Main Street Coffee model — "
               "table-service focus, evening trade, delivery-enabled from Day 1.")
    pdf.bullet("Target catchment: 3,400+ customers; leverage Jnah's menu learnings for opening SKU selection.",
               colour=TEXT_MID)
    pdf.bullet("RISK: Cannibalization if located <2 km from Conut Jnah; single-product dependency on core espresso range.",
               colour=RED)
    pdf.ln(2)

    # ── Objective 2 ─────────────────────────────────────────────────────────
    pdf.section_title("2", "Smart Staffing Optimiser")
    pdf.two_col_table(
        ["Branch", "Top Shift", "Productivity (units/hr)", "Rec. Staff", "Anomalies"],
        [
            ["Conut Jnah",         "Morning + Afternoon", "5.1 M",    "2 core + 1 peak", "2"],
            ["Main Street Coffee", "Afternoon (12-17)",   "3.2 M",    "2 core + 2 peak", "4"],
            ["Conut - Tyre",       "Afternoon (12-17)",   "-",         "2 per shift",    "3"],
            ["Conut (original)",   "Morning (06-12)",     "50 K",     "2 per shift",     "0"],
        ],
        col_widths=[45, 42, 32, 32, 22],
    )
    pdf.bullet("ACTION: Enforce punch-out auto-timeout for shifts exceeding 14 h (9 violations detected).")
    pdf.bullet("Add 1 surge-cover staff at MSC Friday-Saturday evenings based on demand uplift signals.",
               colour=TEXT_MID)
    pdf.bullet("RISK: Conut (original) operating at minimal revenue; consider re-deploying staff to growing branches.",
               colour=RED)


# ---------------------------------------------------------------------------
# Page 2 — Objectives 3, 4, 5 + Actions & Risks
# ---------------------------------------------------------------------------
def build_page2(pdf: BriefPDF):
    pdf.add_page()

    # ── Objective 3 ─────────────────────────────────────────────────────────
    pdf.section_title("3", "Combo & Upsell Recommender (Market Basket Analysis)")
    pdf.kpi_row([
        ("Transactions", "136", BLUE),
        ("Global Rules", "35", BLUE),
        ("Top Lift", "17.00 ×", GREEN),
        ("Branch Rules (MSC)", "142", ACCENT),
    ])
    pdf.two_col_table(
        ["Rule  (Antecedent → Consequent)", "Lift", "Recommended Action"],
        [
            ["SINGLE ESPRESSO + HOT drink",          "17.00x", "Bundle: 'Espresso + Hot Combo' on POS"],
            ["THE SHARING BOX + TRIPLE CHOC MINI",   "15.11x", "Promote 'Sharing Deal' meal"],
            ["CHIMNEY CAKE + ESPRESSO",               "~12x",  "Upsell prompt at cashier"],
            ["CARAMEL FRAPPE + COOKIE ITEM",          "~9x",   "Cross-sell on digital menu"],
        ],
        col_widths=[78, 18, 64],
    )
    pdf.bullet("Implement top-5 combos as 'Meal Deal' promotions in POS system.")
    pdf.bullet("Main Street Coffee has the richest basket data — pilot combo bundles there first.",
               colour=TEXT_MID)
    pdf.bullet("RISK: Low transaction volume at Tyre branch (5 orders); rules may not generalise.",
               colour=RED)
    pdf.ln(1)

    # ── Objective 4 ─────────────────────────────────────────────────────────
    pdf.section_title("4", "Demand Forecast Engine  (Jan - Mar 2026)")
    pdf.two_col_table(
        ["Branch", "Trajectory", "Jan 2026", "Feb 2026", "Mar 2026", "R²"],
        [
            ["Main Street Coffee", "Strongly Accelerating", "4.47 B", "7.87 B",  "13.9 B", "0.88"],
            ["Conut Jnah",         "Strongly Accelerating", "3.31 B", "4.13 B",  "5.16 B", "0.70"],
            ["Conut - Tyre",       "Strongly Accelerating", "1.69 B", "2.04 B",  "2.47 B", "—"],
            ["Conut (original)",   "Declining",             "-",      "-",       "-",      "-"],
            ["NETWORK TOTAL",      "",                      "9.47 B", "13.68 B", "21.79 B", ""],
        ],
        col_widths=[45, 40, 20, 20, 20, 15],
    )
    pdf.small_text(
        "Model: 50% Holt double-exponential smoothing + 30% OLS linear regression + 20% CAGR extrapolation. "
        "Prediction intervals: 80% and 95% CI from residual std.",
        italic=True,
    )
    pdf.bullet("ACTION: Pre-order inventory for MSC at 2× current levels by end of Jan; arrange supplier SLA for Q1.")
    pdf.bullet("Conut (original) trajectory warrants store-format review — potential conversion or closure by Q2.",
               colour=RED)
    pdf.ln(1)

    # ── Objective 5 ─────────────────────────────────────────────────────────
    pdf.section_title("5", "Coffee & Milkshake Growth Strategy")
    pdf.kpi_row([
        ("Total Bev. Revenue", "1.36 B", BLUE),
        ("Coffee Share", "50.7 %", GREEN),
        ("Top OPPORTUNITY", "Pistachio MK", ACCENT),
        ("Items to Prune", "12 DOGs", RED),
        ("Strategies", "5 Plans", BLUE),
    ])
    pdf.two_col_table(
        ["BCG Quadrant", "Top Items", "Recommended Action"],
        [
            ["STAR  (high qty, high rev/unit)",  "OREO MILKSHAKE, HOT CHOC COMBO, CARAMEL FRAPPE",
             "Defend; feature in loyalty rewards"],
            ["OPPORTUNITY  (low qty, high rev/unit)", "PISTACHIO MK (893K/unit), MATCHA FRAPPE (626K/unit)",
             "Promote; add to upsell engine"],
            ["CASH COW  (high qty, low rev/unit)", "Core espresso range",
             "Maintain pricing; combo-bundle to lift margin"],
            ["DOG  (low qty, low rev/unit)", "12 items identified",
             "Remove from menu — free up kitchen capacity"],
        ],
        col_widths=[45, 75, 40],
    )
    pdf.bullet("Launch 'Pistachio & Matcha Week' seasonal campaign to accelerate OPPORTUNITY items into STAR quadrant.")
    pdf.bullet("Introduce milkshake-combo bundles (+15% ASP uplift expected based on combo engine rules).",
               colour=TEXT_MID)
    pdf.bullet("RISK: Pruning 12 DOG items may affect small loyal customer segments; validate with 4-week test-remove.",
               colour=RED)

    pdf.ln(2)
    pdf.divider()

    # ── Consolidated actions & expected impact ──────────────────────────────
    pdf.section_title("->", "Consolidated Actions & Expected Impact")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*DARK_BG)
    pdf.cell(0, 6, _s("Priority Actions (next 90 days):"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    actions = [
        ("Immediate",  "Implement top-5 combo Meal Deals in POS system across all branches"),
        ("Immediate",  "Enforce 14-hour auto-timeout on punch-out system; review 9 flagged anomalies"),
        ("30 days",    "Promote OPPORTUNITY beverages (Pistachio, Matcha) via seasonal campaign"),
        ("30 days",    "Pre-order Q1 inventory for MSC at 2× current levels"),
        ("60 days",    "Remove 12 DOG menu items; audit impact after 4 weeks"),
        ("90 days",    "Site-selection study for 5th branch replicating MSC model"),
        ("90 days",    "Re-evaluate Conut (original) - format change or reallocation of staff to growing sites"),
    ]
    for horizon, action in actions:
        pdf.set_x(pdf.l_margin + 3)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*ACCENT)
        pdf.cell(20, 5, _s(f"[{horizon}]"), new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(pdf.epw - 23, 5, _s(action), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*DARK_BG)
    pdf.cell(0, 6, _s("Expected Impact (12-month horizon):"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    impacts = [
        "+15–25 % basket value uplift from combo promotion programme",
        "+30–40 % beverage revenue via OPPORTUNITY item activation (Pistachio, Matcha)",
        "Network demand 9.47 B → ~21.8 B by Mar 2026 (driven by MSC + Jnah trajectory)",
        "5th branch operational by Q3 2026 replicating MSC at 100/100 score model",
        "Staffing cost rationalisation: reduce anomaly-driven overtime by ~9 shift instances/month",
    ]
    for imp in impacts:
        pdf.bullet(imp, colour=GREEN)

    # ── API / Integration note ───────────────────────────────────────────────
    pdf.ln(1)
    pdf.set_fill_color(*DARK_BG)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 7.5)
    box_y = pdf.get_y()
    pdf.rect(pdf.l_margin, box_y, pdf.epw, 12, "F")
    pdf.set_xy(pdf.l_margin + 3, box_y + 1.5)
    pdf.cell(0, 5, _s("OpenClaw Integration: FastAPI server on port 8000 - all 5 objectives accessible via REST + NLP /ask endpoint"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(pdf.l_margin + 3, box_y + 6.5)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 4,
             _s("GET /health | GET /expansion | GET /staffing/{branch} | GET /combos | GET /forecast/{branch} | GET /coffee-strategy | GET /ask?query=..."),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def generate_brief(output_path: str = "executive_brief.pdf") -> str:
    pdf = BriefPDF()
    build_page1(pdf)
    build_page2(pdf)
    pdf.output(output_path)
    return output_path


if __name__ == "__main__":
    out = generate_brief()
    print(f"[OK] Executive brief saved -> {out}")
