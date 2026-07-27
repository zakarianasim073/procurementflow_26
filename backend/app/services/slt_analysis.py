"""SLT (Significantly Low-Priced Tender) Analysis — PPR 2025 compliance generator."""

import math
import logging
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

THIN = Side(style="thin")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
TITLE_FONT = Font(bold=True, size=14, color="1F4E79")
SECTION_FONT = Font(bold=True, size=11, color="1F4E79")
BOLD = Font(bold=True, size=10)
NUM_FMT = '#,##0.00'
PCT_FMT = '0.00%'
GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
YELLOW_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
LIGHT_BLUE = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")


def _header_row(ws, row, values, col_start=1):
    for i, v in enumerate(values):
        c = ws.cell(row=row, column=col_start + i, value=v)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        c.border = BORDER


def _data_row(ws, row, values, col_start=1, fmt=None, fill=None):
    for i, v in enumerate(values):
        c = ws.cell(row=row, column=col_start + i, value=v)
        c.border = BORDER
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        if fmt and i < len(fmt) and fmt[i]:
            c.number_format = fmt[i]
        if fill:
            c.fill = fill


def generate_slt_analysis(
    oce: float,
    nppi: float,
    current_quote: float,
    assumed_bidders: int = 8,
    output_path: str = "./SLT_Analysis.xlsx",
    tender_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate PPR 2025 SLT Analysis Excel with methodology, recommendations, and scenario analysis.

    Args:
        oce: Official Cost Estimate (BDT)
        nppi: NPPI Index (e.g., 0.891)
        current_quote: Your current quoted amount (BDT)
        assumed_bidders: Typical number of responsive bidders (default: 8)
        output_path: Output Excel path
        tender_info: Optional tender metadata (tender_id, package_no, etc.)

    Returns:
        Path to generated Excel file
    """
    wb = Workbook()

    # ── Sheet 1: Dashboard ──────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "SLT Dashboard"
    ws1.sheet_properties.tabColor = "1F4E79"

    # Column widths
    for col in range(1, 10):
        ws1.column_dimensions[get_column_letter(col)].width = 20

    x_nppi = oce * nppi

    # Title
    ws1.merge_cells("A1:H1")
    c = ws1.cell(row=1, column=1, value="PPR 2025 — SIGNIFICANTLY LOW-PRICED TENDER (SLT) ANALYSIS")
    c.font = TITLE_FONT
    c.alignment = Alignment(horizontal="center")

    r = 3
    _header_row(ws1, r, ["Parameter", "Value (BDT)", "Description"])
    inputs = [
        ("Official Cost Estimate (OCE)", oce, "From tender documents"),
        ("NPPI Index", nppi, "From e-GP portal (avg awarded/estimate ratio)"),
        ("X_NPPI (OCE × NPPI)", x_nppi, "NPPI-adjusted estimate"),
        ("Your Current Quote", current_quote, "Your submitted bid amount"),
        ("Current Discount %", (oce - current_quote) / oce, "Your current discount vs OCE"),
        ("Assumed Bidders", assumed_bidders, "Expected responsive bidder count"),
    ]
    for i, (label, val, desc) in enumerate(inputs):
        row = r + 1 + i
        fmt = [None, None if isinstance(val, int) else (NUM_FMT if isinstance(val, float) and val > 1 else PCT_FMT), None]
        _data_row(ws1, row, [label, val, desc], fmt=fmt)
        ws1.cell(row=row, column=1).font = BOLD
        ws1.cell(row=row, column=1).alignment = Alignment(horizontal="left")

    # ── Recommended Quote Strategies ────────────────────────────────────
    r = 12
    ws1.merge_cells(f"A{r}:H{r}")
    c = ws1.cell(row=r, column=1, value="RECOMMENDED QUOTE STRATEGIES")
    c.font = SECTION_FONT

    r += 1
    _header_row(ws1, r, ["Strategy", "Quote Amount (BDT)", "Discount %", "Risk Level", "Description"])
    avg_bidder_price = oce * 0.97  # Assume bidders average ~3% below OCE
    x_avg = (0.2 * oce) + (0.5 * avg_bidder_price) + (0.3 * x_nppi)
    sd_est = oce * 0.02  # Estimated std dev ~2% of OCE
    slt_threshold = x_avg - sd_est

    conservative = oce - (slt_threshold * 0.85)
    balanced = slt_threshold + (oce - slt_threshold) * 0.15
    aggressive = slt_threshold * 0.98

    strategies = [
        ("Conservative", conservative, (oce - conservative) / oce, "LOW", "Safe from SLT — may not win"),
        ("Balanced (Recommended)", balanced, (oce - balanced) / oce, "MEDIUM", "Optimal win probability"),
        ("Aggressive", aggressive, (oce - aggressive) / oce, "HIGH", "Highest win chance — SLT risk"),
    ]
    fills = [GREEN_FILL, YELLOW_FILL, RED_FILL]
    for i, (name, amount, disc, risk, desc) in enumerate(strategies):
        row = r + 1 + i
        _data_row(ws1, row, [name, amount, disc, risk, desc], fmt=[None, NUM_FMT, PCT_FMT, None, None], fill=fills[i])
        ws1.cell(row=row, column=1).font = BOLD

    # ── Comparison with Current Quote ───────────────────────────────────
    r = 19
    ws1.merge_cells(f"A{r}:H{r}")
    c = ws1.cell(row=r, column=1, value="COMPARISON WITH YOUR CURRENT QUOTE")
    c.font = SECTION_FONT

    r += 1
    _header_row(ws1, r, ["Description", "Amount (BDT)", "Discount %", "Difference (BDT)", "Insight"])
    diff = current_quote - balanced
    _data_row(ws1, r + 1, [
        "Your Current Quote", current_quote, (oce - current_quote) / oce, "", ""
    ], fmt=[None, NUM_FMT, PCT_FMT, None, None])
    _data_row(ws1, r + 2, [
        "Recommended (Balanced)", balanced, (oce - balanced) / oce, "", ""
    ], fmt=[None, NUM_FMT, PCT_FMT, None, None])
    _data_row(ws1, r + 3, [
        "Difference", diff, (current_quote - balanced) / oce if oce else 0, "",
        f"Adjust {'down' if diff > 0 else 'up'} by BDT {abs(diff):,.2f}"
    ], fmt=[None, NUM_FMT, PCT_FMT, None, None], fill=YELLOW_FILL if abs(diff) > 0 else None)

    # ── SLT Calculation Methodology ─────────────────────────────────────
    r = 26
    ws1.merge_cells(f"A{r}:H{r}")
    c = ws1.cell(row=r, column=1, value="PPR 2025 — SLT CALCULATION METHODOLOGY")
    c.font = SECTION_FONT

    r += 1
    _header_row(ws1, r, ["Step", "Description", "Formula", "Example Value"])
    steps = [
        ("1", "Official Cost Estimate", "Xoce (given)", f"BDT {oce:,.2f}"),
        ("2", "Average Price of Responsive Bidders", "Xȑ = Σ(Xi) / n", f"BDT {avg_bidder_price:,.2f} (estimated)"),
        ("3", "NPPI Adjusted Value", "X_NPPI = Xoce × NPPI", f"BDT {x_nppi:,.2f}"),
        ("4", "Weighted Average", "X = 0.2×Xoce + 0.5×Xȑ + 0.3×X_NPPI", f"BDT {x_avg:,.2f}"),
        ("5", "Standard Deviation", "SD = √[Σ(X - Xi)² / n]", f"BDT {sd_est:,.2f} (estimated)"),
        ("6", "SLT Threshold", "SLT = X - SD", f"BDT {slt_threshold:,.2f}"),
    ]
    for i, (step, desc, formula, example) in enumerate(steps):
        row = r + 1 + i
        _data_row(ws1, row, [step, desc, formula, example], fmt=[None, None, None, None])
        ws1.cell(row=row, column=1).font = BOLD
        if i == 5:
            ws1.cell(row=row, column=4).font = Font(bold=True, color="FF0000", size=11)

    # ── Key Insights ────────────────────────────────────────────────────
    r = 36
    ws1.merge_cells(f"A{r}:H{r}")
    c = ws1.cell(row=r, column=1, value="KEY INSIGHTS")
    c.font = SECTION_FONT

    insights = [
        f"1. Your current {(oce - current_quote) / oce * 100:.2f}% discount is {'CONSERVATIVE' if current_quote > balanced else 'AGGRESSIVE'} — {'you are safe from SLT but may not win' if current_quote > balanced else 'you are competitive but at SLT risk'}",
        f"2. SLT threshold (BDT {slt_threshold:,.2f}) = bids below this need justification per PPR 2025",
        f"3. To be the LOWEST bidder, consider quoting around {((oce - balanced) / oce * 100) + 1:.1f}-{((oce - balanced) / oce * 100) + 2:.1f}% below OCE",
        f"4. Recommended quote range: BDT {aggressive:,.2f} to BDT {conservative:,.2f}",
        f"5. The SLT formula: SLT = Weighted Average - Standard Deviation",
        f"6. Weighted Average = 20%×OCE + 50%×Average + 30%×X_NPPI",
    ]
    for i, insight in enumerate(insights):
        row = r + 1 + i
        ws1.merge_cells(f"A{row}:H{row}")
        c = ws1.cell(row=row, column=1, value=insight)
        c.font = Font(size=10)
        c.alignment = Alignment(wrap_text=True)

    # ── Sheet 2: Scenario Analysis ──────────────────────────────────────
    ws2 = wb.create_sheet("Scenario Analysis")
    ws2.sheet_properties.tabColor = "2E75B6"
    for col in range(1, 12):
        ws2.column_dimensions[get_column_letter(col)].width = 18

    ws2.merge_cells("A1:K1")
    c = ws2.cell(row=1, column=1, value="SCENARIO ANALYSIS — OPTIMAL QUOTES BY BIDDER COUNT")
    c.font = TITLE_FONT
    c.alignment = Alignment(horizontal="center")

    _header_row(ws2, 3, ["Bidders", "Scenario", "Lowest Comp", "Optimal Quote", "Discount %", "SLT Threshold",
                          "Margin Below Comp", "Weighted Avg", "Risk", "Win Prob", "Recommendation"])

    scenarios = [
        (7, 1, "Lowest comp @ -6%", 0.9133, 0.9120),
        (7, 2, "Lowest comp @ -2%", 0.9150, 0.9230),
        (7, 3, "Lowest comp @ -8%", 0.9065, 0.9051),
        (8, 1, "Lowest comp @ -7%", 0.9100, 0.9050),
        (8, 2, "Lowest comp @ -4%", 0.9000, 0.8966),
        (8, 3, "Lowest comp @ -8%", 0.9100, 0.9042),
        (9, 1, "Lowest comp @ -5%", 0.9110, 0.9146),
        (9, 2, "Lowest comp @ -3%", 0.9100, 0.9111),
        (9, 3, "Lowest comp @ -5%", 0.9120, 0.9127),
        (10, 1, "Lowest comp @ -8%", 0.9160, 0.9164),
        (10, 2, "Lowest comp @ -5%", 0.9080, 0.9057),
        (10, 3, "Lowest comp @ -7%", 0.9150, 0.9124),
    ]

    for i, (bidders, scenario, label, opt_factor, slt_factor) in enumerate(scenarios):
        row = 4 + i
        optimal = oce * opt_factor
        slt = oce * slt_factor
        comp_price = oce * (0.94 if scenario == 1 else (0.98 if scenario == 2 else 0.92))
        weighted_avg = (comp_price + optimal) / 2
        margin = comp_price - optimal
        disc = (oce - optimal) / oce
        risk = "LOW" if disc < 0.08 else ("MEDIUM" if disc < 0.10 else "HIGH")
        win_prob = "HIGH (>80%)" if disc > 0.10 else ("MEDIUM (50-80%)" if disc > 0.08 else "LOW (<50%)")
        rec = "Recommended" if risk == "MEDIUM" else ("Aggressive" if risk == "HIGH" else "Conservative")

        risk_fill = GREEN_FILL if risk == "LOW" else (YELLOW_FILL if risk == "MEDIUM" else RED_FILL)
        fmt = [None, None, None, NUM_FMT, PCT_FMT, NUM_FMT, NUM_FMT, NUM_FMT, None, None, None]
        _data_row(ws2, row, [bidders, scenario, label, optimal, disc, slt, margin, weighted_avg, risk, win_prob, rec],
                  fmt=fmt, fill=risk_fill)

    # ── Sheet 3: SLT Calculator ─────────────────────────────────────────
    ws3 = wb.create_sheet("SLT Calculator")
    ws3.sheet_properties.tabColor = "548235"
    for col in range(1, 5):
        ws3.column_dimensions[get_column_letter(col)].width = 25

    ws3.merge_cells("A1:D1")
    c = ws3.cell(row=1, column=1, value="SLT CALCULATOR — ENTER BIDDER PRICES")
    c.font = TITLE_FONT
    c.alignment = Alignment(horizontal="center")

    # Input section
    r = 3
    _header_row(ws3, r, ["INPUT", "Value", "", ""])
    calc_inputs = [
        ("Official Cost Estimate (OCE)", oce),
        ("NPPI Index", nppi),
        ("Number of Bidders", assumed_bidders),
    ]
    for i, (label, val) in enumerate(calc_inputs):
        row = r + 1 + i
        _data_row(ws3, row, [label, val, "", ""],
                  fmt=[None, NUM_FMT if isinstance(val, float) and val > 1 else ("0.000" if isinstance(val, float) else None), None, None])
        ws3.cell(row=row, column=1).font = BOLD
        ws3.cell(row=row, column=2).fill = LIGHT_BLUE

    # Bidder price entry table
    r = 9
    _header_row(ws3, r, ["Bidder", "Quoted Price (BDT)", "Discount %", "Deviation from Avg"])
    sample_prices = [
        (1, oce * 0.94), (2, oce * 0.95), (3, oce * 0.96),
        (4, oce * 0.97), (5, oce * 0.98), (6, oce * 1.00),
        (7, 0), (8, 0), (9, 0), (10, 0),
    ]
    entered = [p for _, p in sample_prices if p > 0]
    avg_price = sum(entered) / len(entered) if entered else 0
    for i, (bidder, price) in enumerate(sample_prices):
        row = r + 1 + i
        disc = (oce - price) / oce if price > 0 else 0
        dev = price - avg_price if price > 0 else 0
        fmt_row = [None, NUM_FMT if price > 0 else None, PCT_FMT if price > 0 else None, NUM_FMT if price > 0 else None]
        _data_row(ws3, row, [f"Bidder {bidder}", price if price > 0 else "", disc if price > 0 else "", dev if price > 0 else ""],
                  fmt=fmt_row, fill=LIGHT_BLUE if price > 0 else None)

    # Calculated values
    r = 22
    _header_row(ws3, r, ["CALCULATED VALUES", "Value", "", ""])

    n = len(entered)
    sum_prices = sum(entered)
    x_nppi_calc = oce * nppi
    x_avg_calc = 0.2 * oce + 0.5 * avg_price + 0.3 * x_nppi_calc
    variance = sum((x_avg_calc - p) ** 2 for p in entered) / n if n > 0 else 0
    sd_calc = math.sqrt(variance)
    slt_calc = x_avg_calc - sd_calc

    calc_results = [
        ("X_NPPI", x_nppi_calc),
        ("Count of Bidders (n)", n),
        ("Sum of Prices", sum_prices),
        ("Average Price (Xȑ)", avg_price),
        ("Weighted Average (X)", x_avg_calc),
        ("Standard Deviation (SD)", sd_calc),
        ("SLT THRESHOLD", slt_calc),
    ]
    for i, (label, val) in enumerate(calc_results):
        row = r + 1 + i
        is_slt = "SLT" in label
        _data_row(ws3, row, [label, val, "", ""],
                  fmt=[None, NUM_FMT, None, None],
                  fill=RED_FILL if is_slt else PatternFill())
        ws3.cell(row=row, column=1).font = Font(bold=True, size=11, color="FF0000" if is_slt else "000000")

    # Save
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out))
    logger.info(f"SLT Analysis generated: {out}")
    return str(out)
