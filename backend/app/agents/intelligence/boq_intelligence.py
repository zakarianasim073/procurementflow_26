"""
Agent 5 — BOQ Intelligence Agent
Parses Bill of Quantities from PDF/XLSX, classifies items, normalizes units, validates quantities.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Dict, List, Optional

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agent_schemas import BOQItem
from app.services.pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class BOQIntelligenceAgent(BaseAgent):
    agent_id = "agent-005-boq-intelligence"
    agent_name = "BOQ Intelligence Agent"
    description = "Parses Bill of Quantities from PDF/XLSX, classifies line items, normalizes units, and validates quantities."
    dependencies: List[str] = ["agent-004-document-ai"]
    version = "2.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_id = context.get("tender_id", "eGP-001")
        boq_path = context.get("boq_path", "")
        upstream = context.get("upstream", {})
        acquisition = upstream.get("agent-002-tender-acquisition", {})
        documents = acquisition.get("documents", {})

        if not boq_path:
            file_paths = context.get("file_paths") or {}
            boq_path = file_paths.get("boq", "") if isinstance(file_paths, dict) else ""
        if not boq_path and isinstance(documents, dict):
            boq_path = documents.get("BOQ", "") or documents.get("boq", "")
        if not boq_path and isinstance(documents, list):
            for item in documents:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("doc_type") or item.get("type") or item.get("name") or "").lower()
                if "boq" in label:
                    boq_path = str(item.get("path") or item.get("file_path") or "")
                    break
        if not boq_path or not os.path.isfile(boq_path):
            boq_path = context.get("boq_path_fallback", "")
            if not os.path.isfile(boq_path):
                boq_path = ""

        items = []
        if boq_path and boq_path.endswith('.pdf'):
            items = await asyncio.to_thread(self._parse_pdf_boq, boq_path)

        if not items:
            items = await self._try_brain_boq(tender_id)

        if not items:
            items = self._generate_demo_items(tender_id)

        classified = self._classify_items(items)
        validated = self._validate_quantities(classified)
        normalized = self._normalize_units(validated)

        # Analyze BOQ vs APP estimate deviations
        deviation_analysis = {}
        try:
            from app.services.deviation_analyzer import DeviationAnalyzerService
            items_for_analysis = [
                {
                    "item_no": i.item_no,
                    "code": i.sor_code,
                    "desc": i.description,
                    "qty": i.quantity,
                    "rate": i.rate,
                    "sor_rate": getattr(i, "sor_rate", None),
                    "flag": i.validation_notes if not i.is_valid else None,
                }
                for i in normalized
            ]
            deviation_analysis = await asyncio.to_thread(
                DeviationAnalyzerService.analyze_boq_vs_app,
                items_for_analysis,
                tender_id,
            )
            logger.info("Deviation analysis for %s: %d APP records found", tender_id, deviation_analysis.get("app_records_found", 0))
        except Exception as e:
            logger.debug("Deviation analysis failed for %s: %s", tender_id, e)

        output = {
            "total_items": len(normalized),
            "items": [
                {
                    "item_no": i.item_no,
                    "description": i.description,
                    "unit": i.unit,
                    "quantity": i.quantity,
                    "rate": i.rate,
                    "amount": i.amount,
                    "category": i.category,
                    "sor_code": i.sor_code,
                    "is_valid": i.is_valid,
                    "validation_notes": i.validation_notes,
                }
                for i in normalized
            ],
            "categories_found": list(set(i.category for i in normalized if i.category)),
            "categories_count": len(set(i.category for i in normalized if i.category)),
            "deviation_analysis": deviation_analysis,
        }

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=output,
        )

    def _parse_pdf_boq(self, path: str) -> List[BOQItem]:
        """Parse BOQ items from a PDF using pdf_parser with fallback to text extraction."""
        try:
            parser = PDFParser()
            import asyncio
            raw_items = asyncio.run(parser.extract_boq_items(path))
            if raw_items:
                return [
                    BOQItem(
                        item_no=i.get("item_no", idx + 1),
                        description=i.get("description", ""),
                        unit=self._normalize_unit(i.get("unit", "")),
                        quantity=float(i.get("quantity", 0) or 0),
                        sor_code=i.get("code", ""),
                        is_valid=True,
                    )
                    for idx, i in enumerate(raw_items)
                ]
        except Exception as e:
            logger.debug(f"PDFParser failed: {e}, falling back to text extraction")

        items = []
        try:
            import fitz
            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()

            lines = text.split('\n')
            in_table = False
            for line in lines:
                line = line.strip()
                if "Bill of Quantities" in line or "Item" in line:
                    in_table = True
                    continue
                if not in_table:
                    continue

                item_match = re.match(
                    r'(\d+)\s+([\d-]+)?\s*([\d-]+)?\s*(.*?)\s+'
                    r'(cum|sqm|sqft|each|kg|ton|no|nos|ls|lump\s*sum|mtr|km)\s*'
                    r'([\d,]+(?:\.\d+)?)',
                    line, re.IGNORECASE
                )
                if item_match:
                    item_no = int(item_match.group(1))
                    group = item_match.group(2) or ""
                    code = item_match.group(3) or ""
                    description = item_match.group(4).strip()
                    unit = item_match.group(5).strip().lower()
                    qty_str = item_match.group(6).replace(',', '')
                    try:
                        qty = float(qty_str)
                    except ValueError:
                        continue

                    items.append(BOQItem(
                        item_no=item_no,
                        description=description,
                        unit=self._normalize_unit(unit),
                        quantity=qty,
                        sor_code=code or group,
                        is_valid=True,
                    ))
                elif in_table and re.match(r'^Total|^Grand|^$', line):
                    break

            if items:
                return items

        except ImportError:
            logger.warning("PyMuPDF not available for BOQ parsing")
        except Exception as e:
            logger.debug(f"BOQ PDF parsing error: {e}")

        return self._generate_demo_items(os.path.basename(path))

    async def _try_brain_boq(self, tender_id: str) -> List[BOQItem]:
        """Try to get BOQ items from brain knowledge store."""
        try:
            entries = await self.query_brain("boq_text", tender_id)
            if entries:
                for entry in entries:
                    data = entry.get("data", {})
                    text = data.get("text", "") or data.get("content", "") or str(data)
                    if len(text) > 100:
                        items = self._parse_boq_text(text)
                        if items:
                            return items
        except Exception as e:
            logger.debug(f"Brain BOQ lookup failed: {e}")
        return []

    def _parse_boq_text(self, text: str) -> List[BOQItem]:
        """Parse BOQ items from raw text using the pdf_parser logic."""
        items = []
        lines = text.split('\n')
        in_table = False
        for line in lines:
            line = line.strip()
            if "Bill of Quantities" in line or "Item" in line:
                in_table = True
                continue
            if not in_table:
                continue
            item_match = re.match(
                r'(\d+)\s+([\d-]+)?\s*([\d-]+)?\s*(.*?)\s+'
                r'(cum|sqm|sqft|each|kg|ton|no|nos|ls|lump\s*sum|mtr|km)\s*'
                r'([\d,]+(?:\.\d+)?)',
                line, re.IGNORECASE
            )
            if item_match:
                item_no = int(item_match.group(1))
                group = item_match.group(2) or ""
                code = item_match.group(3) or ""
                description = item_match.group(4).strip()
                unit = item_match.group(5).strip().lower()
                qty_str = item_match.group(6).replace(',', '')
                try:
                    qty = float(qty_str)
                except ValueError:
                    continue
                items.append(BOQItem(
                    item_no=item_no,
                    description=description,
                    unit=self._normalize_unit(unit),
                    quantity=qty,
                    sor_code=code or group,
                    is_valid=True,
                ))
            elif in_table and re.match(r'^Total|^Grand|^$', line):
                break
        return items

    def _generate_demo_items(self, tender_id: str) -> List[BOQItem]:
        """No demo items — return empty. Real BOQ data comes from PDF parsing or brain knowledge."""
        return []

    def _classify_items(self, items: List[BOQItem]) -> List[BOQItem]:
        mapping = {
            "earth": "Earthwork", "cutting": "Earthwork", "filling": "Earthwork",
            "dredged": "Earthwork", "sand": "Earthwork", "excavation": "Earthwork",
            "brick": "Civil Works", "soling": "Civil Works",
            "block": "Concrete", "rcc": "Concrete", "cement": "Concrete",
            "reinforcement": "Steel", "steel": "Steel",
            "formwork": "Civil Works", "geotextile": "Civil Works",
            "stone": "Civil Works", "pitching": "Civil Works",
            "turfing": "Other", "survey": "Other",
        }
        for item in items:
            desc_lower = item.description.lower()
            for keyword, category in mapping.items():
                if keyword in desc_lower:
                    item.category = category
                    break
        return items

    def _normalize_units(self, items: List[BOQItem]) -> List[BOQItem]:
        unit_map = {
            "cum": "cum", "cubic meter": "cum", "cubic metre": "cum", "m3": "cum",
            "sqm": "sqm", "square meter": "sqm", "square metre": "sqm", "m2": "sqm",
            "each": "each", "ea": "each", "no": "each", "nos": "each",
            "kg": "kg", "kilogram": "kg", "ton": "ton", "tonne": "ton",
            "lump_sum": "lump_sum", "ls": "lump_sum", "lump sum": "lump_sum",
            "km": "km", "mtr": "m", "meter": "m",
        }
        for item in items:
            item.unit = unit_map.get(item.unit.lower(), item.unit)
        return items

    def _normalize_unit(self, unit: str) -> str:
        unit_map = {
            "cum": "cum", "cubic meter": "cum", "cubic metre": "cum", "m3": "cum",
            "sqm": "sqm", "square meter": "sqm", "square metre": "sqm", "m2": "sqm",
            "each": "each", "ea": "each", "no": "each", "nos": "each",
            "kg": "kg", "ton": "ton",
            "ls": "lump_sum", "lump sum": "lump_sum",
        }
        return unit_map.get(unit.lower(), unit)

    def _validate_quantities(self, items: List[BOQItem]) -> List[BOQItem]:
        for item in items:
            notes = []
            valid = True
            if item.quantity <= 0:
                valid = False
                notes.append("Invalid quantity (zero or negative)")
            if item.unit == "each" and item.quantity > 500_000:
                valid = False
                notes.append(f"Unusually large count: {item.quantity}")
            if item.unit == "cum" and item.quantity > 500_000:
                valid = False
                notes.append(f"Unusually large volume: {item.quantity}")
            item.is_valid = valid
            item.validation_notes = "; ".join(notes) if notes else "Valid"
        return items
