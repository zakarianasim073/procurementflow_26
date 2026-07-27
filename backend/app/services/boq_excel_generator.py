from __future__ import annotations

"""BOQ Excel Generator — Generate BOQ Rate Analysis Excel in 5-tab format.
Produces: Tender Summary, BOQ Rate Comparison, Work Type Summary,
           Rate Detail & Flags, Financial Check
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, numbers
from openpyxl.utils import get_column_letter
from app.services.market_index import market_index as market_index_svc

logger = logging.getLogger(__name__)

HEADER_FONT = Font(bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
TITLE_FONT = Font(bold=True, size=14, color="2F5496")
SUBTITLE_FONT = Font(bold=True, size=12, color="2F5496")
LABEL_FONT = Font(bold=True, size=10)
NORMAL_FONT = Font(size=10)
GREEN_FONT = Font(size=10, color="006600")
RED_FONT = Font(size=10, color="CC0000")
ORANGE_FONT = Font(size=10, color="CC6600")
SECTION_FONT = Font(bold=True, size=10, color="2F5496")
SECTION_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
WARN_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
ALERT_FILL = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
NOCODE_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)

WORK_TYPE_KEYWORDS = {
    "Preliminaries": ["preparation of site", "site office", "preliminaries", "mobilization"],
    "Earthwork": ["earth work", "excavation", "filling", "cutting", "ditch", "pond", "lead"],
    "Filter Works": ["filter", "sand filter", "jhama chips", "geo-tex filter"],
    "CC Blocks & Dumping": ["cc block", "c.c. block", "dumping", "boulder", "concrete block"],
    "Geo-Bags / Geotextile": ["geo-bag", "geotextile", "geo-textile", "salvaging"],
    "Structural Concrete": ["rcc", "reinforced", "centering", "shuttering", "ms rod", "mass concrete"],
    "Finishing": ["plaster", "paint", "tile", "brick work", "brick flat", "soling"],
    "Electrical": ["cable", "led", "solar", "pole", "stay", "bracket", "board", "breaker", "earthing", "circuit"],
    "Labour": ["head man", "labour", "skilled", "unskilled"],
}

ZONE_DIVISIONS = {"A": "Dhaka/Mymensingh", "B": "Chattogram/Sylhet", "C": "Rajshahi/Rangpur (BWDB) / Khulna/Barishal (LGED)", "D": "Khulna/Barishal (BWDB) / Rajshahi/Rangpur (LGED)"}
ZONE_NAMES = {"A": "Zone A (Central)", "B": "Zone B (SE & NE)", "C": "Zone C (SW/S/W/E)", "D": "Zone D (N & NW)"}


def classify_work_type(description: str, code: str = "") -> str:
    desc_lower = (description + " " + code).lower()
    for wtype, keywords in WORK_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return wtype
    return "Other"


def _derive_status(sor_rate: float, quoted_rate: float, match_type: str, has_code: bool) -> str:
    if sor_rate == 0 and quoted_rate == 0:
        return "MANUAL REVIEW"
    if sor_rate == 0 and quoted_rate > 0:
        return "NO SOR RATE"
    if sor_rate > 0 and quoted_rate == 0:
        return "SOR AUTO-FILL" if has_code else "DESC SOR-FILL"
    if sor_rate > 0 and quoted_rate > 0:
        variance = (quoted_rate - sor_rate) / sor_rate
        if abs(variance) <= 0.01:
            return "AT SOR (QUOTED)"
        if variance < -0.10:
            return "BELOW SOR"
        if variance > 0.05:
            return "ABOVE SOR"
        return "VARIANCE"
    return "MANUAL REVIEW"


def _fmt_bdt(val) -> str:
    try:
        v = float(val)
        return f"BDT {v:,.2f}"
    except (TypeError, ValueError):
        return str(val) if val else ""


class BOQExcelGenerator:
    """Generate BOQ Rate Analysis Excel in standard 6-tab format.
    Tabs: Tender Summary, BOQ Rate Comparison, Work Type Summary,
           Rate Detail & Flags, Financial Check, Rate Analysis
    """

    def __init__(self, tender_data: Dict[str, Any], boq_items: List[Dict[str, Any]], zone: str = "D"):
        self.tender = tender_data
        self.items = boq_items
        self.zone = zone

        self.total_sor = sum(it.get('sor_rate', 0) * it.get('quantity', 0) for it in boq_items)
        self.total_quoted = sum(it.get('quoted_rate', 0) * it.get('quantity', 0) for it in boq_items)
        self.estimated_cost_app = tender_data.get("estimated_cost_app")

        auto_filled = sum(1 for it in boq_items if it.get('quoted_rate', 0) == 0 and it.get('sor_rate', 0) > 0)
        no_code = sum(1 for it in boq_items if not it.get('code', ''))
        filled_by_sor = sum(1 for it in boq_items if it.get('flag') in ("SOR AUTO-FILL", "DESC SOR-FILL")
                            or (it.get('quoted_rate', 0) == 0 and it.get('sor_rate', 0) > 0))
        self.auto_filled_count = auto_filled
        self.no_code_count = no_code
        self.filled_by_sor_count = filled_by_sor

    def generate(self, output_path: str) -> str:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        self._build_tender_summary(wb)
        self._build_boq_comparison(wb)
        self._build_work_type_summary(wb)
        self._build_rate_detail_flags(wb)
        self._build_financial_check(wb)
        self._build_rate_analysis_tab(wb)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        wb.save(output_path)
        logger.info(f"BOQ Excel saved: {output_path}")
        return output_path

    def _get_status_fill(self, status: str):
        if status in ("SOR AUTO-FILL", "DESC SOR-FILL"):
            return WARN_FILL
        if status in ("BELOW SOR", "ABOVE SOR"):
            return ALERT_FILL
        if status == "NO SOR RATE":
            return NOCODE_FILL
        return None

    # ─── Sheet 1: Tender Summary ─────────────────────────────────────
    def _build_tender_summary(self, wb: openpyxl.Workbook):
        ws = wb.create_sheet("Tender Summary", 0)
        for col, w in [('A', 3), ('B', 24), ('C', 28), ('D', 15), ('E', 18), ('F', 22)]:
            ws.column_dimensions[col].width = w

        t = self.tender
        saving = self.total_sor - self.total_quoted
        discount_pct = round((saving / self.total_sor * 100), 2) if self.total_sor else 0
        zone_label = ZONE_DIVISIONS.get(self.zone, self.zone)

        # Header
        ws.cell(3, 3, f"BOQ vs SOR RATE ANALYSIS - TENDER ID: {t.get('tender_id', '')}").font = TITLE_FONT
        ws.cell(4, 3, f"{t.get('package_no', '')} - {t.get('package_description', t.get('brief', ''))}").font = SUBTITLE_FONT

        info_rows = [
            (6, "Procuring Entity", t.get("procuring_entity", t.get("organization", ""))),
            (7, "Location / District", t.get("location", t.get("district", ""))),
            (8, "Agency / SOR", t.get("sor_agency", "BWDB Schedule of Rates")),
            (9, "Zone Applied", f"Zone {self.zone} ({zone_label})"),
            (10, "Invitation Ref.", t.get("invitation_ref", "")),
            (11, "Tender ID", str(t.get("tender_id", ""))),
            (12, "Tender Security", t.get("tender_security_text", "")),
            (13, "Closing Date", t.get("tender_close_datetime", "")),
            (14, "Work Period", t.get("work_period", "")),
            (15, "Report Generated", datetime.now().strftime("%d-%b-%Y %H:%M")),
        ]
        for r, label, val in info_rows:
            ws.cell(r, 3, label).font = LABEL_FONT
            ws.cell(r, 5, str(val)[:80]).font = NORMAL_FONT

        # Financial comparison: APP estimate vs SOR vs Quoted
        r = 17
        ws.cell(r, 3, "COST COMPARISON").font = SUBTITLE_FONT
        r += 1

        def cost_row(label, amount, bold=False):
            nonlocal r
            ws.cell(r, 3, label).font = LABEL_FONT if bold else NORMAL_FONT
            fmt = _fmt_bdt(amount)
            ws.cell(r, 5, fmt).font = HEADER_FONT if bold else NORMAL_FONT
            if bold:
                for c in range(3, 7):
                    ws.cell(r, c).fill = SECTION_FILL
            r += 1
            return r

        r = cost_row("Estimated Cost (APP)", self.estimated_cost_app)
        r = cost_row("Total SOR Amount (SOR rates x Qty)", self.total_sor)
        r = cost_row("Total Quoted Amount (as per BOQ)", self.total_quoted)

        if self.estimated_cost_app and self.total_sor:
            sor_vs_app = self.total_sor - self.estimated_cost_app
            sor_vs_app_pct = (sor_vs_app / self.estimated_cost_app) * 100
            ws.cell(r, 3, "SOR vs APP Variance").font = LABEL_FONT
            ws.cell(r, 5, _fmt_bdt(sor_vs_app)).font = RED_FONT if abs(sor_vs_app_pct) > 20 else GREEN_FONT
            ws.cell(r, 6, f"{sor_vs_app_pct:+.2f}%").font = RED_FONT if abs(sor_vs_app_pct) > 20 else GREEN_FONT
            r += 1

        r = cost_row("Saving vs SOR", saving)
        r = cost_row(f"Discount ({discount_pct:.2f}%)", None)

        # Items summary
        ws.cell(r + 1, 3, "ITEMS SUMMARY").font = SUBTITLE_FONT
        item_summary = [
            (r + 2, "Total BOQ Items", len(self.items)),
            (r + 3, "SOR-matched (code or description)", len(self.items) - self.auto_filled_count - self.no_code_count),
            (r + 4, "Auto-filled from SOR (rate not quoted)", self.filled_by_sor_count),
            (r + 5, "No SOR Code (description-matched)", self.no_code_count),
        ]
        for rr, label, val in item_summary:
            ws.cell(rr, 3, label).font = LABEL_FONT
            ws.cell(rr, 5, str(val)).font = NORMAL_FONT

        # TDS Requirements
        r2 = r + 7
        ws.cell(r2, 3, "QUALIFICATION REQUIREMENTS (TDS)").font = SUBTITLE_FONT
        tds_fields = [
            ("Experience (General)", "experience_general"),
            ("Experience (Specific)", "experience_specific"),
            ("Annual Turnover (AACT)", "annual_turnover"),
            ("Financial Resources", "financial_resources"),
            ("Min Tender Capacity", "tender_capacity"),
            ("Personnel", "personnel"),
            ("Equipment", "equipment"),
            ("JV", "jv_notes"),
        ]
        for i, (label, key) in enumerate(tds_fields):
            val = t.get(key, "")
            ws.cell(r2 + 1 + i, 3, label).font = LABEL_FONT
            ws.cell(r2 + 1 + i, 5, str(val)[:80]).font = NORMAL_FONT

    # ─── Sheet 2: BOQ Rate Comparison ────────────────────────────────
    def _build_boq_comparison(self, wb: openpyxl.Workbook):
        ws = wb.create_sheet("BOQ Rate Comparison", 1)

        headers = ["#", "Item Code", "Match By", "Work Type", "Description of Item",
                   "Unit", "Quantity", "SOR Rate", "SOR Amount",
                   "Quoted Rate", "Quoted Amount",
                   "Rate Diff", "Variance %", "Status"]

        ws.cell(1, 1, f'BOQ vs SOR RATE COMPARISON - Tender {self.tender.get("tender_id", "")}').font = TITLE_FONT
        ws.cell(2, 1, f'LEGEND: SOR AUTO-FILL=rate from SOR (bidder not quoted) | DESC SOR-FILL=description match (no code) | AT SOR=quoted at SOR | BELOW/ABOVE SOR=bidder quoted below/above').font = Font(size=9, italic=True)
        ws.cell(3, 1, f'Zone {self.zone} applied | APP Estimate: {_fmt_bdt(self.estimated_cost_app)} | SOR Total: {_fmt_bdt(self.total_sor)}').font = Font(size=9, italic=True)

        for c, h in enumerate(headers, 1):
            cell = ws.cell(4, c, h)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(wrap_text=True, horizontal='center')
            cell.border = THIN_BORDER

        widths = [4, 14, 9, 18, 50, 7, 10, 12, 14, 12, 14, 12, 10, 16]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        work_type_order = [
            "Preliminaries", "Earthwork", "Filter Works", "Geo-Bags / Geotextile",
            "CC Blocks & Dumping", "Structural Concrete", "Finishing",
            "Electrical", "Labour", "Other"
        ]

        row = 4
        for wt in work_type_order:
            wt_items = [it for it in self.items if it.get('work_type', classify_work_type(it.get('description', ''), it.get('code', ''))) == wt]
            if not wt_items:
                continue

            row += 1
            ws.cell(row, 1, f">  {wt}")
            ws.cell(row, 1).font = SECTION_FONT
            for c in range(1, len(headers) + 1):
                ws.cell(row, c).fill = SECTION_FILL

            for item in wt_items:
                row += 1
                code = item.get('code', '') or ''
                desc = item.get('description', '')
                unit = item.get('unit', '')
                qty = item.get('quantity', 0)
                sor_rate = item.get('sor_rate', 0) or 0
                quoted_rate = item.get('quoted_rate', 0) or 0
                match_type = item.get('match_type', '')
                has_code = bool(code.strip())

                sor_amt = sor_rate * qty
                quoted_amt = quoted_rate * qty
                rate_diff = quoted_rate - sor_rate
                variance = rate_diff / sor_rate if sor_rate else 0

                # Determine match method display
                if has_code and match_type in ("exact_code", "prefix_code"):
                    match_by = "Code" if match_type == "exact_code" else "Prefix"
                elif match_type == "description":
                    match_by = "Description"
                elif not has_code:
                    match_by = "No Code"
                else:
                    match_by = "-"

                status = _derive_status(sor_rate, quoted_rate, match_type, has_code)

                ws.cell(row, 1, item.get('item_no', ''))
                ws.cell(row, 2, code)
                ws.cell(row, 3, match_by)
                ws.cell(row, 4, wt)
                ws.cell(row, 5, desc[:120])
                ws.cell(row, 6, unit)
                ws.cell(row, 7, qty)
                ws.cell(row, 8, sor_rate)
                ws.cell(row, 9, round(sor_amt, 2))
                ws.cell(row, 10, quoted_rate if quoted_rate else "(auto-fill)")
                ws.cell(row, 11, round(quoted_amt, 2) if quoted_rate else "(auto)")
                ws.cell(row, 12, round(rate_diff, 2))
                ws.cell(row, 13, round(variance * 100, 2))
                ws.cell(row, 14, status)

                fill = self._get_status_fill(status)
                for c in range(1, 15):
                    ws.cell(row, c).font = NORMAL_FONT
                    ws.cell(row, c).border = THIN_BORDER
                    if fill:
                        ws.cell(row, c).fill = fill

        # Grand total
        row += 2
        ws.cell(row, 1, "GRAND TOTAL").font = HEADER_FONT
        for c in range(1, 15):
            ws.cell(row, c).fill = SECTION_FILL
        ws.cell(row, 9, round(self.total_sor, 2)).font = HEADER_FONT
        ws.cell(row, 11, round(self.total_quoted, 2)).font = HEADER_FONT
        ws.cell(row, 12, round(self.total_quoted - self.total_sor, 2)).font = HEADER_FONT

    # ─── Sheet 3: Work Type Summary ──────────────────────────────────
    def _build_work_type_summary(self, wb: openpyxl.Workbook):
        ws = wb.create_sheet("Work Type Summary", 2)

        headers = ["Work Type", "Items", "SOR Amount (BDT)", "Quoted Amount (BDT)",
                   "Saving (BDT)", "Discount %", "% of Quoted Total"]

        ws.cell(1, 1, f'WORK TYPE COST SUMMARY - Tender {self.tender.get("tender_id", "")}').font = TITLE_FONT
        ws.cell(2, 1, f'Total SOR: {_fmt_bdt(self.total_sor)} | Total Quoted: {_fmt_bdt(self.total_quoted)}').font = Font(size=9, italic=True)
        ws.cell(3, 1, f'APP Estimate: {_fmt_bdt(self.estimated_cost_app)}').font = Font(size=9, italic=True)

        for c, h in enumerate(headers, 1):
            cell = ws.cell(4, c, h)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.border = THIN_BORDER

        widths = [28, 8, 20, 20, 18, 14, 18]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        work_types = {}
        for item in self.items:
            wt = item.get('work_type', classify_work_type(item.get('description', ''), item.get('code', '')))
            if wt not in work_types:
                work_types[wt] = {'count': 0, 'sor_amt': 0, 'quoted_amt': 0}
            work_types[wt]['count'] += 1
            work_types[wt]['sor_amt'] += item.get('sor_rate', 0) * item.get('quantity', 0)
            work_types[wt]['quoted_amt'] += item.get('quoted_rate', 0) * item.get('quantity', 0)

        total_quoted = sum(v['quoted_amt'] for v in work_types.values())

        row = 4
        for wt, data in sorted(work_types.items(), key=lambda x: -x[1]['sor_amt']):
            row += 1
            saving = data['sor_amt'] - data['quoted_amt']
            discount = saving / data['sor_amt'] if data['sor_amt'] else 0
            pct_of_total = data['quoted_amt'] / total_quoted if total_quoted else 0

            ws.cell(row, 1, wt).font = NORMAL_FONT
            ws.cell(row, 2, data['count']).font = NORMAL_FONT
            ws.cell(row, 3, round(data['sor_amt'], 2)).font = NORMAL_FONT
            ws.cell(row, 4, round(data['quoted_amt'], 2)).font = NORMAL_FONT
            ws.cell(row, 5, round(saving, 2)).font = NORMAL_FONT
            ws.cell(row, 6, round(discount * 100, 2)).font = NORMAL_FONT
            ws.cell(row, 7, round(pct_of_total * 100, 2)).font = NORMAL_FONT
            for c in range(1, 8):
                ws.cell(row, c).border = THIN_BORDER

        # Summary row
        row += 1
        ws.cell(row, 1, "APP ESTIMATE vs SOR vs QUOTED").font = HEADER_FONT
        for c in range(1, 8):
            ws.cell(row, c).fill = HEADER_FILL
        row += 1
        ws.cell(row, 1, "Estimated Cost (APP)").font = LABEL_FONT
        ws.cell(row, 3, self.estimated_cost_app or "N/A").font = NORMAL_FONT
        row += 1
        ws.cell(row, 1, "SOR Variance vs APP").font = LABEL_FONT
        if self.estimated_cost_app and self.total_sor:
            sor_vs_app_pct = ((self.total_sor - self.estimated_cost_app) / self.estimated_cost_app) * 100
            ws.cell(row, 3, f"{sor_vs_app_pct:+.2f}%").font = RED_FONT if abs(sor_vs_app_pct) > 20 else GREEN_FONT

    # ─── Sheet 4: Rate Detail & Flags ─────────────────────────────────
    def _build_rate_detail_flags(self, wb: openpyxl.Workbook):
        ws = wb.create_sheet("Rate Detail & Flags", 3)

        headers = ["#", "Code", "Match By", "Description", "Unit", "Qty",
                   "SOR Rate", "Quoted Rate", "Saving/Unit", "Total Saving", "Status"]

        ws.cell(1, 1, 'RATE DETAIL - FLAGGED ITEMS FOR REVIEW').font = TITLE_FONT
        ws.cell(2, 1, 'Items auto-filled from SOR (yellow), items without SOR code (green), items above/below SOR (orange)').font = Font(size=9, italic=True)

        for c, h in enumerate(headers, 1):
            cell = ws.cell(3, c, h)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.border = THIN_BORDER

        widths = [4, 14, 10, 50, 7, 8, 12, 12, 12, 16, 16]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        row = 3
        for item in self.items:
            row += 1
            code = item.get('code', '') or ''
            desc = item.get('description', '')
            unit = item.get('unit', '')
            qty = item.get('quantity', 0)
            sor_rate = item.get('sor_rate', 0) or 0
            quoted_rate = item.get('quoted_rate', 0) or 0
            match_type = item.get('match_type', '')
            has_code = bool(code.strip())

            saving_per_unit = quoted_rate - sor_rate
            total_saving = saving_per_unit * qty

            if has_code and match_type in ("exact_code", "prefix_code"):
                match_by = "Code" if match_type == "exact_code" else "Prefix"
            elif match_type == "description":
                match_by = "Description"
            elif not has_code:
                match_by = "No Code"
            else:
                match_by = "-"

            status = _derive_status(sor_rate, quoted_rate, match_type, has_code)

            ws.cell(row, 1, item.get('item_no', ''))
            ws.cell(row, 2, code)
            ws.cell(row, 3, match_by)
            ws.cell(row, 4, (desc or '')[:100])
            ws.cell(row, 5, unit)
            ws.cell(row, 6, qty)
            ws.cell(row, 7, sor_rate)
            ws.cell(row, 8, quoted_rate if quoted_rate else "(auto-fill)")
            ws.cell(row, 9, round(saving_per_unit, 2))
            ws.cell(row, 10, round(total_saving, 2))

            if sor_rate == 0 and quoted_rate == 0:
                status_display = "MANUAL REVIEW"
            elif quoted_rate == 0 and sor_rate > 0:
                status_display = "AUTO-FILL"
            elif sor_rate == 0 and quoted_rate > 0:
                status_display = "NO SOR RATE"
            else:
                status_display = status
            ws.cell(row, 11, status_display)

            fill = self._get_status_fill(status)
            for c in range(1, 12):
                ws.cell(row, c).font = NORMAL_FONT
                ws.cell(row, c).border = THIN_BORDER
                if fill:
                    ws.cell(row, c).fill = fill

    # ─── Sheet 5: Financial Check ────────────────────────────────────
    def _build_financial_check(self, wb: openpyxl.Workbook):
        ws = wb.create_sheet("Financial Check", 4)

        headers = ["", "Criterion", "Required", "Our Figure", "Remarks", "Status"]

        ws.cell(1, 1, f'FINANCIAL QUALIFICATION CHECKLIST').font = TITLE_FONT
        ws.cell(2, 1, f'Tender: {self.tender.get("tender_id", "")} | {self.tender.get("package_no", "")}').font = Font(size=9, italic=True)

        for c, h in enumerate(headers, 1):
            cell = ws.cell(3, c, h)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.border = THIN_BORDER

        widths = [3, 30, 30, 30, 35, 14]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        # Build financial items dynamically from tender_data + APP estimate
        app_est = self.estimated_cost_app or 0
        if app_est:
            ts_bdt = app_est * 0.02  # 2% tender security
            aact_req = app_est * 0.5  # 50% AACT
            loc_req = app_est * 0.25  # 25% LoC
            specific_exp_req = app_est * 0.4  # 40% specific experience
            tender_cap_req = app_est * 0.6  # 60% tender capacity
        else:
            ts_bdt = 6100000
            aact_req = 242000000
            loc_req = 85000000
            specific_exp_req = 121000000
            tender_cap_req = 182000000

        check_items = [
            ("Avg Annual Construction Turnover", f"Min Tk. {aact_req:,.0f}", "See audit/turnover cert.",
             "AACT >= required over 5 yrs", "Review"),
            ("Financial Resource (Line of Credit)", f"Min Tk. {loc_req:,.0f}",
             "NCC Bank LoC", "Form e-PW3-8", "OK"),
            ("Tender Capacity (A x N x 1.25 - B)", f"Min Tk. {tender_cap_req:,.0f}",
             "Max annual work capacity", "N = completion years", "Review"),
            ("Tender Security", _fmt_bdt(ts_bdt), "BG from Bank", "Form e-PW3-7", "OK"),
            ("Specific Experience", f"1 contract >= Tk. {specific_exp_req:,.0f}",
             "Similar work completion cert.", "Match work type", "Review"),
            ("SOR Amount vs APP Estimate", f"SOR={_fmt_bdt(self.total_sor)} vs APP={_fmt_bdt(app_est)}",
             "Check if SOR total exceeds APP by >20%",
             f"Variance: {((self.total_sor - app_est) / app_est * 100):+.2f}%" if app_est else "N/A",
             "ALERT" if (app_est and abs(self.total_sor - app_est) / app_est > 0.20) else "OK"),
            ("Items Auto-filled", f"{self.filled_by_sor_count} of {len(self.items)} items",
             "Rates filled from SOR (not quoted)", "Verify against market", "Review" if self.filled_by_sor_count > 0 else "OK"),
            ("No-Code Items", f"{self.no_code_count} items without SOR code",
             "Matched by description only", "Verify match accuracy", "Review" if self.no_code_count > 0 else "OK"),
            ("JV Agreement", "e-PW3-B + Tk. 300 stamp", "JV deed submitted", "Notarial stamp verified", "OK"),
            ("Tax Documents", "TIN + IT Return + VAT", "All submitted", "Income tax year current", "OK"),
            ("Ongoing Works Declaration", "Signed list", "Must declare all ongoing + JV %", "Verify accuracy", "Review"),
        ]

        for r, (criterion, required, figure, remarks, status) in enumerate(check_items, 4):
            ws.cell(r, 2, criterion).font = LABEL_FONT
            ws.cell(r, 3, str(required)[:60]).font = NORMAL_FONT
            ws.cell(r, 4, figure).font = NORMAL_FONT
            ws.cell(r, 5, str(remarks)[:60]).font = NORMAL_FONT

            status_color = "008000"
            if status == "ALERT":
                status_color = "CC0000"
            elif status == "Review":
                status_color = "CC6600"
            ws.cell(r, 6, status).font = Font(bold=True, color=status_color)

            for c in range(1, 7):
                ws.cell(r, c).border = THIN_BORDER

        # Zone verification note
        r = 4 + len(check_items) + 1
        ws.cell(r, 2, "ZONE VERIFICATION").font = SUBTITLE_FONT
        r += 1
        ws.cell(r, 2, f"Zone {self.zone} applied for SOR rate lookup").font = LABEL_FONT
        ws.cell(r, 4, ZONE_NAMES.get(self.zone, "Unknown")).font = NORMAL_FONT
        r += 1
        ws.cell(r, 2, f"District: {self.tender.get('district', self.tender.get('location', 'N/A'))}").font = LABEL_FONT
        ws.cell(r, 4, f"Maps to Zone {self.zone}" if self.zone else "Not mapped").font = NORMAL_FONT


    # ─── Sheet 6: Rate Analysis — Element Breakdown & Profit Margin ───
    def _build_rate_analysis_tab(self, wb: openpyxl.Workbook):
        """6th tab: element-wise breakdown with market prices & profit margin."""
        from app.services.rate_analysis_engine import analyze_boq_items

        ws = wb.create_sheet("Rate Analysis", 5)

        headers = [
            "Item No", "SOR Code", "Description", "Unit", "Qty",
            "BOQ Rate", "SOR Rate",
            "Sub-Item", "Component", "Template Unit", "Template Qty",
            "Market Source", "Market Unit", "Market Rate/Unit",
            "Market Cost/Work Unit", "% of Market Cost",
            "BOQ Amt/Unit", "Market Cost/Unit", "Profit vs Market %",
            "SOR vs Market %", "Bid vs SOR %",
        ]

        # Title
        ws.cell(1, 1, f'ELEMENT-WISE RATE ANALYSIS WITH MARKET PRICES — Tender {self.tender.get("tender_id", "")}').font = TITLE_FONT
        ws.cell(2, 1, f'Zone {self.zone} applied for market price adjustment').font = Font(size=9, italic=True)
        ws.cell(3, 1, f'Market prices sourced from {market_index_svc._data.get("source", "BBS/REHAB")}').font = Font(size=9, italic=True)
        ws.cell(3, 1).font = Font(size=9, italic=True, color="666666")

        # Legend
        ws.cell(4, 1, 'LEGEND: Profit vs Market % > 15% = SAFE | 5-15% = TIGHT | < 5% = AT RISK | Negative = LOSS').font = Font(size=9, italic=True, color="CC6600")

        for c, h in enumerate(headers, 1):
            cell = ws.cell(5, c, h)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(wrap_text=True, horizontal='center')
            cell.border = THIN_BORDER

        widths = [6, 14, 36, 6, 8, 12, 12, 32, 12, 10, 10, 18, 10, 13, 16, 12, 12, 14, 14, 14, 12]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        # Build enriched items
        enriched_items = []
        for item in self.items:
            enriched_items.append({
                "item_no": item.get("item_no", item.get("serial", "")),
                "code": item.get("code", "") or item.get("sor_source", ""),
                "description": item.get("desc", "") or item.get("description", ""),
                "unit": item.get("unit", ""),
                "quantity": item.get("qty", 0) or item.get("quantity", 0),
                "quoted_rate": item.get("rate") or item.get("quoted_rate", 0),
                "sor_rate": item.get("sor_rate", 0),
            })

        # Run rate analysis engine on all items
        logger.info(f"Running element-wise rate analysis for {len(enriched_items)} items (zone={self.zone})")
        analyzed = analyze_boq_items(enriched_items, self.zone)

        row = 5
        has_any_analysis = False

        for item in analyzed:
            ra = item.get("rate_analysis", {})
            if not ra.get("has_composition"):
                continue

            has_any_analysis = True
            elements = ra.get("elements", [])
            pcts = ra.get("pct_of_cost", [])
            total_market_per_unit = ra.get("total_market_cost_per_unit", 0)
            quoted_rate = ra.get("quoted_rate")
            sor_rate = ra.get("sor_rate")
            profit_market = ra.get("profit_margin_vs_market")
            sor_vs_market = ra.get("sor_vs_market_pct")
            bid_vs_sor = ra.get("margin_vs_sor")

            # Item header row
            row += 1
            ws.cell(row, 1, item.get("item_no", "")).font = SECTION_FONT
            ws.cell(row, 2, ra.get("sor_code", "")).font = SECTION_FONT
            ws.cell(row, 3, (ra.get("description", "") or "")[:80]).font = SECTION_FONT
            ws.cell(row, 4, ra.get("unit", "")).font = SECTION_FONT
            ws.cell(row, 5, ra.get("quantity", "")).font = SECTION_FONT
            ws.cell(row, 6, quoted_rate).font = SECTION_FONT
            ws.cell(row, 7, sor_rate).font = SECTION_FONT
            for c in range(1, 22):
                ws.cell(row, c).fill = SECTION_FILL
                ws.cell(row, c).border = THIN_BORDER

            # Profit summary in item header
            if profit_market is not None:
                ws.cell(row, 17, quoted_rate)
                ws.cell(row, 18, total_market_per_unit)
                ws.cell(row, 19, profit_market)
                pm_fill = GREEN_FONT if profit_market > 15 else (ORANGE_FONT if profit_market > 5 else RED_FONT)
                ws.cell(row, 19).font = pm_fill
            if sor_vs_market is not None:
                ws.cell(row, 20, sor_vs_market)
            if bid_vs_sor is not None:
                ws.cell(row, 21, bid_vs_sor)

            row += 1
            ws.cell(row, 8, "SUMMARY").font = Font(bold=True, size=9, color="2F5496")
            ws.cell(row, 15, total_market_per_unit).font = Font(bold=True, size=9)
            ws.cell(row, 16, "100%").font = Font(bold=True, size=9)
            ws.cell(row, 17, quoted_rate).font = Font(bold=True, size=9)
            ws.cell(row, 18, total_market_per_unit).font = Font(bold=True, size=9)
            if profit_market is not None:
                ws.cell(row, 19, profit_market).font = Font(bold=True, size=9)
            if sor_vs_market is not None:
                ws.cell(row, 20, sor_vs_market).font = Font(bold=True, size=9)
            if bid_vs_sor is not None:
                ws.cell(row, 21, bid_vs_sor).font = Font(bold=True, size=9)
            for c in range(1, 22):
                ws.cell(row, c).border = THIN_BORDER

            # Sub-item rows
            for idx, (el, pct) in enumerate(zip(elements, pcts)):
                row += 1
                ws.cell(row, 8, el.get("sub_desc", "")[:60])
                ws.cell(row, 9, el.get("component", ""))
                ws.cell(row, 10, el.get("template_unit", ""))
                ws.cell(row, 11, el.get("template_qty", ""))
                ws.cell(row, 12, el.get("market_source", ""))
                ws.cell(row, 13, el.get("market_unit", ""))
                ws.cell(row, 14, el.get("market_rate_per_unit", ""))
                ws.cell(row, 15, el.get("market_cost_per_work_unit", ""))
                if pct is not None:
                    ws.cell(row, 16, pct)

                for c in range(1, 22):
                    ws.cell(row, c).font = Font(size=9)
                    ws.cell(row, c).border = THIN_BORDER

        if not has_any_analysis:
            row += 2
            ws.cell(row, 1, "No BOQ items have recognized SOR codes with rate analysis templates.").font = Font(size=10, italic=True, color="CC0000")
            ws.cell(row + 1, 1, "Rate analysis requires items with SOR codes matching BWDB patterns (e.g., 28-100, 40-200).").font = Font(size=9, italic=True, color="666666")


def generate_boq_excel(
    tender_data: Dict[str, Any],
    boq_items: List[Dict[str, Any]],
    zone: str = "D",
    output_path: str = "./boq_rate_analysis.xlsx"
) -> str:
    """Generate BOQ Rate Analysis Excel with 5 tabs."""
    for item in boq_items:
        if 'work_type' not in item:
            item['work_type'] = classify_work_type(
                item.get('description', ''),
                item.get('code', '')
            )

    gen = BOQExcelGenerator(tender_data, boq_items, zone)
    return gen.generate(output_path)
