"""BOQ Processor - Parses BOQ files and compares against SOR rates"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

from app.core import helpers, calculations, work_type, match_helpers
from app.agents.core.envelope import build_envelope
try:
    from app.core.excel_writer import write_boq_analysis
except ModuleNotFoundError:
    write_boq_analysis = None
try:
    from app.core.docx_writer import write_boq_docx
except ModuleNotFoundError:
    write_boq_docx = None


def _norm_code(c: str) -> str:
    """Normalize code for comparison (strip agency suffixes, separators, lowercase)."""
    c = re.sub(r'\(pwd\)|\(lged\)|\(bwdb\)', '', c, flags=re.I)
    return c.replace(" ", "").replace("-", "").replace(".", "").replace("&", "").lower()


def _has_meaningful_code(code: str) -> bool:
    """Reject e-GP item serials like 1, 2, 10 as SOR item codes."""
    code = (code or "").strip()
    if not code or re.fullmatch(r"\d{1,3}", code):
        return False
    return bool(re.search(r"[A-Za-z.-]", code) and re.search(r"\d", code))


def _zone_label(zone: Optional[str | dict]) -> str:
    if isinstance(zone, dict):
        return ", ".join(f"{ag}=Z{z}" for ag, z in sorted(zone.items()))
    if isinstance(zone, str) and zone.strip():
        return f"Zone {zone.upper()}"
    return "N/A"


class BOQProcessor:
    def __init__(self):
        self.boq_items = []

    async def compare(
        self,
        boq_path: str,
        sor_agency: str = "BWDB",
        zone: Optional[str | dict] = None,
        sor_service: Any = None,
        tender_info: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Parse BOQ file and compare rates against SOR."""
        try:
            self.boq_items = await self._parse_boq(boq_path)
            comparison_results = self._compare_with_sor(sor_agency, zone, sor_service, tender_info)
            summary = self._create_summary(comparison_results)
            arithmetic_errors = self.check_arithmetic(self.boq_items)
            flagged = [r for r in comparison_results
                       if r.get("flag") in ("VARIANCE", "BELOW SOR", "ABOVE SOR")]

            # Compare against all three SORs every time; keep the label explicit.
            zone_label = _zone_label(zone)
            if isinstance(tender_info, dict) and zone_label == "N/A":
                inferred = tender_info.get("district") or tender_info.get("location") or tender_info.get("procuring_entity_district")
                if inferred:
                    zone_label = str(inferred)

            estimated_cost_app = (tender_info or {}).get("estimated_cost_app")
            info = {
                "tender_id": (tender_info or {}).get("tender_id", "N/A"),
                "title": (tender_info or {}).get("title", ""),
                "entity": (tender_info or {}).get("entity") or "BWDB / PWD / LGED",
                "location": (tender_info or {}).get("location", ""),
                "sor_agency": "BWDB / PWD / LGED Schedule of Rates",
                "zone": zone_label or "N/A",
                "estimated_cost_app": estimated_cost_app,
                "total_sor": summary.get("total_sor", 0),
                "total_quoted": summary.get("total_quoted", 0),
                "saving": summary.get("total_sor", 0) - summary.get("total_quoted", 0),
                "discount_pct": summary.get("discount_pct", 0),
                "qualifications": (tender_info or {}).get("qualifications", []),
            }

            # Generate Excel and DOCX
            gen = self._generate_excel(
                info, comparison_results,
                summary.get("by_work_type", []),
                flagged,
                (tender_info or {}).get("financial_check", [])
            )

            return {
                "success": True, "data": comparison_results,
                "summary": summary, "flagged": flagged,
                "excel_path": gen.get("excel_path"),
                "docx_path": gen.get("docx_path"),
                "tenderai_dir": gen.get("tenderai_dir", ""),
                "comparison_scope": "multi_agency",
                "agencies_compared": ["BWDB", "PWD", "LGED"],
                "total_items": len(comparison_results),
                "mismatches": sum(1 for r in comparison_results if r.get("flag") in ("ABOVE SOR", "MISMATCH")),
                "variances": sum(1 for r in comparison_results if r.get("flag") == "VARIANCE"),
                "matches": sum(1 for r in comparison_results if r.get("flag") == "AT SOR"),
                "below_sor": sum(1 for r in comparison_results if r.get("flag") == "BELOW SOR"),
                "arithmetic_errors": arithmetic_errors,
                "arithmetic_error_count": len(arithmetic_errors),
                # W-009: L6 envelope (deterministic comparison -> HIGH)
                "envelope": build_envelope(
                    value={
                        "total_items": len(comparison_results),
                        "flagged": len(flagged),
                        "arithmetic_error_count": len(arithmetic_errors),
                    },
                    confidence="HIGH",
                    evidence=(
                        [f"item {e['item_no'] or e['code']}: stated {e['stated_amount']} vs computed {e['computed_amount']}" for e in arithmetic_errors]
                        + [f"item {r.get('item_no', '')}: {r.get('flag')}" for r in flagged[:50]]
                    ) or ["No variance or arithmetic flags"],
                    rule_version="boq-sor-compare+arithmetic r1",
                    knowledge_refs=["BWDB/PWD/LGED Schedule of Rates"],
                ),
            }
        except Exception as e:
            raise Exception(f"BOQ comparison failed: {str(e)}")

    @staticmethod
    def check_arithmetic(items: List[Dict]) -> List[Dict]:
        """W-008: flag every line where quantity x rate != stated amount.

        Tolerance covers BDT rounding only (1 Tk or 0.5%, whichever is larger);
        items missing any of the three values are skipped, never guessed.
        """
        errors: List[Dict] = []
        for item in items:
            qty = helpers.to_num(item.get("quantity"))
            rate = helpers.to_num(item.get("rate"))
            amount = helpers.to_num(item.get("amount"))
            if qty is None or rate is None or amount is None:
                continue
            computed = round(qty * rate, 2)
            tolerance = max(1.0, abs(computed) * 0.005)
            if abs(computed - amount) > tolerance:
                errors.append({
                    "item_no": item.get("item_no", ""),
                    "code": item.get("code", ""),
                    "description": item.get("description", ""),
                    "quantity": qty,
                    "rate": rate,
                    "stated_amount": amount,
                    "computed_amount": computed,
                    "difference": round(amount - computed, 2),
                    "flag": "ARITHMETIC ERROR",
                })
        return errors

    async def _parse_boq(self, file_path: str) -> List[Dict]:
        path = Path(file_path)
        if path.suffix.lower() == ".pdf":
            return await self._parse_boq_pdf(file_path)
        elif path.suffix.lower() in (".xlsx", ".xls"):
            return await self._parse_boq_excel(file_path)
        elif path.suffix.lower() == ".txt":
            return await self._parse_boq_text(file_path)
        raise ValueError(f"Unsupported format: {path.suffix}")

    async def _parse_boq_pdf(self, pdf_path: str) -> List[Dict]:
        from .pdf_parser import PDFParser
        return await PDFParser().extract_boq_items(pdf_path)

    async def _parse_boq_excel(self, excel_path: str) -> List[Dict]:
        from .excel_parser import ExcelParser
        return await ExcelParser().extract_boq_items(excel_path)

    async def _parse_boq_text(self, text_path: str) -> List[Dict]:
        """Parse authenticated e-GP BOQ text exports, including no-code tables."""
        raw = Path(text_path).read_text(encoding="utf-8", errors="ignore")
        raw = raw.replace("\x02", "-").replace("\u00a0", " ")
        lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines()]
        lines = [line for line in lines if line]

        units = {
            "sqm", "sq.m", "sq.m.", "cum", "cu.m", "m", "meter", "kg", "ton",
            "nos", "no", "each", "set", "lump", "l.s", "rft", "cft", "sft",
        }

        def is_unit(value: str) -> bool:
            return value.lower().strip().replace(" ", "") in {u.replace(" ", "") for u in units}

        def is_qty(value: str) -> bool:
            return bool(re.fullmatch(r"\d[\d,]*(?:\.\d+)?", value.replace(" ", "")))

        def is_code_like(value: str) -> bool:
            value = value.strip()
            return bool(
                re.fullmatch(r"\d{1,3}", value)
                or re.search(r"\d{2,3}[-.]\d", value)
                or re.search(r"^(?:PWD|EM)", value, re.I)
            )

        items: List[Dict[str, Any]] = []
        i = 0
        while i < len(lines):
            if not re.fullmatch(r"\d{1,3}", lines[i]):
                i += 1
                continue

            item_no = int(lines[i])
            cursor = i + 1
            code_idx = None
            while cursor < len(lines):
                if is_code_like(lines[cursor]):
                    code_idx = cursor
                    break
                cursor += 1
            if code_idx is None:
                i += 1
                continue

            group = " ".join(lines[i + 1:code_idx]).strip()
            raw_code = lines[code_idx].strip()
            code = raw_code if _has_meaningful_code(raw_code) else ""

            desc_start = code_idx + 1
            unit_idx = None
            cursor = desc_start
            while cursor + 1 < len(lines):
                if is_unit(lines[cursor]) and is_qty(lines[cursor + 1]):
                    unit_idx = cursor
                    break
                if lines[cursor].lower() == "fill by":
                    break
                cursor += 1
            if unit_idx is None:
                i += 1
                continue

            description = " ".join(lines[desc_start:unit_idx]).strip()
            unit = lines[unit_idx].lower().replace("sq.m.", "sqm").replace("sq.m", "sqm")
            quantity = float(lines[unit_idx + 1].replace(",", ""))

            items.append({
                "item_no": item_no,
                "group": group,
                "code": code,
                "description": description[:1000],
                "unit": unit,
                "quantity": quantity,
            })

            cursor = unit_idx + 2
            while cursor < len(lines):
                if lines[cursor].lower() == "auto":
                    auto_count = 0
                    while cursor < len(lines) and lines[cursor].lower() == "auto":
                        auto_count += 1
                        cursor += 1
                    if auto_count >= 3:
                        break
                if re.fullmatch(r"\d{1,3}", lines[cursor]) and cursor > unit_idx + 4:
                    break
                cursor += 1
            i = cursor

        return items

    def _compare_with_sor(self, agency: str, zone: Optional[str | dict],
                          sor_service: Any, tender_info: Optional[dict] = None) -> List[Dict]:
        """Compare BOQ items against SOR rates across all agencies."""
        results = []

        # Get all available agencies for cross-matching
        all_agencies = ['BWDB', 'PWD', 'LGED']
        if sor_service and hasattr(sor_service, 'list_agencies'):
            available = sor_service.list_agencies()
            if available:
                all_agencies = available

        # Zone can be a string (same for all) or a dict keyed by agency
        def get_zone_for_agency(ag: str) -> Optional[str]:
            if isinstance(zone, dict):
                return zone.get(ag, zone.get('default', None))
            if isinstance(zone, str) and zone.strip():
                return zone
            location = ""
            if isinstance(tender_info, dict):
                location = str(
                    tender_info.get("district")
                    or tender_info.get("location")
                    or tender_info.get("procuring_entity_district")
                    or ""
                ).strip()
            if not location:
                return None
            try:
                from app.agents.pricing.sor_zone_matcher import DISTRICT_ZONES
            except Exception:
                return None

            loc = location.lower().replace(" ", "").replace("'", "").replace("-", "").replace(".", "")
            for zone_name, districts in DISTRICT_ZONES.get(ag, {}).items():
                for district in districts:
                    norm_district = district.lower().replace(" ", "").replace("'", "").replace("-", "").replace(".", "")
                    if loc == norm_district or (len(loc) > 4 and (loc in norm_district or norm_district in loc)):
                        return zone_name
            return None

        for item in self.boq_items:
            code = helpers.norm(item.get("code", ""))
            desc = helpers.norm(item.get("description", ""))
            qty = helpers.to_num(item.get("quantity", 0)) or 0.0
            boq_rate = helpers.to_num(item.get("rate"))
            unit = helpers.norm(item.get("unit", ""))

            sor_rate_val, sor_record = None, None
            is_exact_match = False
            match_type = ""
            match_confidence = 0.0
            remarks = ""
            # Agency suffix (PWD)/(LGED)/(BWDB) or code pattern can hint at agency,
            # but we still compare all three SORs on every run.
            detected_agency = self._detect_agency(code) or agency
            # Sub-item code (e.g. "40-620-20") is already extracted by pdf_parser

            if sor_service:
                if detected_agency not in all_agencies:
                    detected_agency = agency if agency in all_agencies else all_agencies[0]
                agencies_to_try = [detected_agency] + [a for a in all_agencies if a != detected_agency]

                # PASS 1: exact code match
                if _has_meaningful_code(code):
                    for try_agency in agencies_to_try:
                        z = get_zone_for_agency(try_agency)
                        sr_val, sr_rec = sor_service.find_rate(code, desc, try_agency, z)
                        if sr_rec and _norm_code(code) == _norm_code(sr_rec.code):
                            sor_rate_val, sor_record = sr_val, sr_rec
                            detected_agency = try_agency
                            is_exact_match = True
                            match_type = "exact_code"
                            match_confidence = 1.0
                            break

                # PASS 2: collect all non-exact matches, prefer prefix over fuzzy
                if not is_exact_match:
                    best_val, best_rec, best_agency = None, None, None
                    best_score = 0.0
                    if _has_meaningful_code(code):
                        for try_agency in agencies_to_try:
                            z = get_zone_for_agency(try_agency)
                            sr_val, sr_rec = sor_service.find_rate(code, desc, try_agency, z)
                            if sr_rec is None:
                                continue
                            bq_n = _norm_code(code)
                            sr_n = _norm_code(sr_rec.code)
                            if len(bq_n) >= 3 and (sr_n.startswith(bq_n) or bq_n.startswith(sr_n)):
                                best_val, best_rec, best_agency = sr_val, sr_rec, try_agency
                                match_type = "prefix_code"
                                best_score = 0.78
                                break
                    if best_rec is None and hasattr(sor_service, "find_rate_by_description"):
                        for try_agency in agencies_to_try:
                            z = get_zone_for_agency(try_agency)
                            sr_val, sr_rec, sr_score = sor_service.find_rate_by_description(
                                desc, try_agency, z, unit=unit, threshold=0.42
                            )
                            if sr_rec is not None and sr_score > best_score:
                                best_val, best_rec, best_agency = sr_val, sr_rec, try_agency
                                best_score = sr_score
                                match_type = "description"
                    if best_val is not None:
                        sor_rate_val, sor_record = best_val, best_rec
                        detected_agency = best_agency
                        match_confidence = best_score

            # Auto-fill from exact/prefix/description match. Description-only matches
            # retain confidence metadata for estimator review.
            if boq_rate is None and sor_rate_val is not None and (is_exact_match or match_type in {"prefix_code", "description"}):
                boq_rate = sor_rate_val
                if match_type == "description":
                    remarks = f"DESC MATCH {match_confidence:.0%}"
            elif boq_rate is None:
                remarks = "SOR NOT FOUND"

            diff = None
            pct_diff = None
            if boq_rate is not None and sor_rate_val is not None:
                diff = calculations.variance(boq_rate, sor_rate_val)
                pct_diff = calculations.pct_variance(boq_rate, sor_rate_val)

            flag = self._get_flag(pct_diff, sor_rate_val, boq_rate)
            wtype = work_type.classify_work_type(desc)

            results.append({
                "item_no": item.get("item_no", ""),
                "code": code,
                "agency": detected_agency,
                "work_type": wtype.title() if wtype else "",
                "desc": desc[:200] if desc else "",
                "unit": unit,
                "qty": qty,
                "rate": boq_rate,
                "sor_rate": sor_rate_val,
                "sor_source": sor_record.code if sor_record else None,
                "sor_desc": sor_record.description[:200] if sor_record else "",
                "match_type": match_type,
                "match_confidence": match_confidence,
                "diff": diff,
                "pct_diff": pct_diff,
                "flag": flag if remarks != "SOR NOT FOUND" else "SOR NOT FOUND",
                "remarks": remarks,
                "section": self._assign_section(wtype),
            })

        return results

    def _get_flag(self, pct: Optional[float], sor: Optional[float],
                  boq: Optional[float]) -> str:
        if sor is None:
            return "SOR MISSING"
        if boq is None:
            return "RATE MISSING"
        if pct is None:
            return "AT SOR"
        if pct < -10:
            return "BELOW SOR"
        if pct > 10:
            return "ABOVE SOR"
        if abs(pct) <= 1:
            return "AT SOR"
        return "VARIANCE"

    def _detect_agency(self, code: str) -> str:
        import re
        c = code.upper()
        # 1. Explicit suffix (PWD)/(LGED)/(BWDB)
        if "(PWD)" in c or c.startswith("PWD ") or c.startswith("EM"):
            return "PWD"
        if "(LGED)" in c:
            return "LGED"
        if "(BWDB)" in c:
            return "BWDB"
        # 2. Pattern-based fallback (patterns are perfectly disjoint per DB analysis)
        clean = code.strip()
        # BWDB: strict 2-3-2 dash pattern (e.g., 40-200-00)
        if re.match(r'^\d{2}-\d{3}-\d{2}$', clean):
            return "BWDB"
        # PWD: dotted, 2-digit prefix (e.g., 26.50.1)
        if re.match(r'^\d{2}\.', clean):
            return "PWD"
        # LGED: dotted, 1-digit prefix [2-9] (e.g., 4.09.01.01)
        if re.match(r'^[2-9]\.', clean):
            return "LGED"
        return ""
    def _assign_section(self, wtype: str) -> str:
        """Map work type to section name, deriving labels from work_type module rules."""
        # Build mapping dynamically from work_type.WORK_TYPE_RULES so labels stay in sync
        section_labels = {
            "earthwork": "Earthwork",
            "concrete": "Concrete & RCC",
            "protection": "Protection Works",
            "finishing": "Finishing",
            "electrical": "Electrical",
            "structural": "Structural",
        }
        return section_labels.get(wtype, wtype.title() if wtype else "Other")

    def _create_summary(self, results: List[Dict]) -> Dict[str, Any]:
        sd = {}
        ts = tq = 0.0
        for item in results:
            qty = item.get("qty", 0.0)
            sor = item.get("sor_rate") or 0
            quoted = item.get("rate") or 0
            sa = float(qty) * float(sor)
            qa = float(qty) * float(quoted)
            ts += sa
            tq += qa
            wtype = work_type.classify_work_type(item.get("desc", ""))
            if wtype not in sd:
                sd[wtype] = {"items": 0, "sor_amount": 0.0, "quoted_amount": 0.0}
            sd[wtype]["items"] += 1
            sd[wtype]["sor_amount"] += sa
            sd[wtype]["quoted_amount"] += qa

        rows = []
        for wt, d in sd.items():
            rows.append({
                "work_type": wt.title(), "items": d["items"],
                "sor_amount": d["sor_amount"], "quoted_amount": d["quoted_amount"],
                "saving": d["sor_amount"] - d["quoted_amount"],
                "discount_pct": (d["sor_amount"] - d["quoted_amount"]) / d["sor_amount"] if d["sor_amount"] else 0,
                "pct_of_total": d["quoted_amount"] / tq if tq else 0,
            })

        return {
            "by_work_type": rows, "total_sor": ts, "total_quoted": tq,
            "discount_pct": (ts - tq) / ts if ts else 0,
        }

    def _generate_excel(self, info: dict, results: list, summary: list,
                        flagged: list, financial: list) -> dict:
        from app.core.config import settings
        tender_id = info.get("tender_id", "unknown")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save to tenderai/{tender_id}/ (user-facing folder on shared storage)
        tenderai_dir = Path(settings.TENDERAI_DIR) / tender_id
        tenderai_dir.mkdir(parents=True, exist_ok=True)
        base_fn = f"BOQ_Analysis_{tender_id}"

        xlsx_fp = ""
        try:
            if write_boq_analysis is None:
                raise RuntimeError("xlsxwriter is not installed")
            xlsx_fp = str(tenderai_dir / f"{base_fn}.xlsx")
            write_boq_analysis(xlsx_fp, info, results, summary, flagged, financial)
        except Exception as e:
            print(f"  Excel generation skipped: {e}")
            xlsx_fp = ""

        docx_fp = ""
        try:
            if write_boq_docx is None:
                raise RuntimeError("python-docx is not installed")
            docx_fp = str(tenderai_dir / f"{base_fn}.docx")
            write_boq_docx(docx_fp, info, results, summary, flagged, financial)
        except Exception as e:
            print(f"  DOCX generation skipped: {e}")
            docx_fp = ""

        # Also try saving to local outputs/ (for API export access)
        ts_fp_xlsx = ""
        ts_fp_docx = ""
        try:
            out = Path(settings.BASE_DIR) / "outputs"
            out.mkdir(parents=True, exist_ok=True)
            ts_fn = f"boq_comparison_{ts}"
            ts_fp_xlsx = str(out / f"{ts_fn}.xlsx")
            if write_boq_analysis is None:
                raise RuntimeError("xlsxwriter is not installed")
            write_boq_analysis(ts_fp_xlsx, info, results, summary, flagged, financial)
            try:
                if write_boq_docx is None:
                    raise RuntimeError("python-docx is not installed")
                ts_fp_docx = str(out / f"{ts_fn}.docx")
                write_boq_docx(ts_fp_docx, info, results, summary, flagged, financial)
            except Exception:
                ts_fp_docx = ""
        except Exception as e:
            print(f"  Timestamp copy skipped: {e}")

        # T-010: mirror generated reports into the object store (outputs/ layout);
        # local files kept — mirror-write transition, rollback = STORAGE_BACKEND=local
        excel_object_key = None
        docx_object_key = None
        try:
            from app.services.storage_service import storage_service, content_type_for
            final_xlsx = xlsx_fp or ts_fp_xlsx
            final_docx = docx_fp or ts_fp_docx
            if final_xlsx:
                excel_object_key = storage_service.store_file(
                    storage_service.object_key("outputs", tender_id, Path(final_xlsx).name),
                    final_xlsx, content_type_for(final_xlsx),
                )
            if final_docx:
                docx_object_key = storage_service.store_file(
                    storage_service.object_key("outputs", tender_id, Path(final_docx).name),
                    final_docx, content_type_for(final_docx),
                )
        except Exception as e:
            print(f"  Object store mirror skipped: {e}")

        return {
            "excel_path": xlsx_fp or ts_fp_xlsx,
            "docx_path": docx_fp or ts_fp_docx,
            "tenderai_dir": str(tenderai_dir),
            "excel_object_key": excel_object_key,
            "docx_object_key": docx_object_key,
        }
