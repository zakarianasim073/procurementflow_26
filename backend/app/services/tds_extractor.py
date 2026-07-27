"""TDS Criteria Extractor Service

Extracts financial qualification criteria from TDS (Tender Data Sheet) PDFs.
Used by agent-006-spec-intelligence and the BOQ comparison pipeline.

Criteria extracted:
  - general_experience (years)
  - specific_experience_value (Tk. X Lakh)
  - specific_experience_count (number of contracts)
  - avg_annual_turnover (Tk. X Lakh)
  - liquid_assets (Tk. X Lakh)
  - min_tender_capacity (Tk. X Lakh)
  - tender_security (Tk. X Lakh)
  - performance_security (%)
  - retention_money (%)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pdfplumber

logger = logging.getLogger(__name__)


class TDSCriteriaExtractor:
    """Extracts financial qualification criteria from TDS PDF text."""

    # Regex patterns for e-GP TDS bracket format + Indian numbering
    PATTERNS = {
        "general_experience": [
            # \b(\d{1,2})\b: calendar years (2023, FY 2025) must never match as experience
            r"minimum number of years of General Experience.*?shall be\s+\b(\d{1,2})\b",
            r"general experience.*?shall be\s+\b(\d{1,2})\b\s*years?",
            r"general experience of at least\s+\b(\d{1,2})\b\s*years?",
        ],
        "specific_experience_value": [
            r"each with a value of at least Tk\.?\s*([\d,]+\.?\d*)\s*Lakh",
            r"value of at least Tk\.?\s*([\d,]+\.?\d*)\s*Lakh",
            r"each of value at least Tk\.?\s*([\d,]+\.?\d*)\s*Lakh",
        ],
        "specific_experience_count": [
            r"at least\s+(\d+)\s*\(?\w*\)?\s*(?:one|contract|similar)",
            r"minimum Specific Experience.*?(\d+)\s+\(?\w*\)?\s*contract",
            r"experience in\s+(\d+)\s+contract",
        ],
        "avg_annual_turnover": [
            r"average annual construction turnover.*?greater than Tk\.?\s*([\d,]+\.?\d*)\s*Lakh",
            r"average annual turnover.*?Tk\.?\s*([\d,]+\.?\d*)\s*Lakh",
            r"annual turnover.*?greater than Tk\.?\s*([\d,]+\.?\d*)\s*Lakh",
        ],
        "liquid_assets": [
            r"financial resources.*?shall be Tk\s*([\d,]+\.?\d*)\s*Lakh",
            r"liquid assets.*?shall be Tk\s*([\d,]+\.?\d*)\s*Lakh",
            r"financial capability.*?Tk\s*([\d,]+\.?\d*)\s*Lakh",
        ],
        "min_tender_capacity": [
            r"minimum tender capacity shall be:\s*([\d,]+\.?\d*)\s*Lakh",
            r"tender capacity.*?shall be\s*([\d,]+\.?\d*)\s*Lakh",
        ],
        "tender_security": [
            r"Tender Security shall be Tk\.?\s*([\d,]+\.?\d*)\s*Lakh",
            r"tender security.*?Tk\.?\s*([\d,]+\.?\d*)\s*Lakh",
            r"bid security.*?Tk\.?\s*([\d,]+\.?\d*)\s*Lakh",
        ],
        "performance_security": [
            r"at the rate of\s*(?:five|5)\s*\(?(\d+)\)?\s*percent.*?Performance Security",
            r"rate of\s*(?:five|5)\s*\(?(\d+)\)?\s*percent.*?performance",
            r"performance security.*?\(?(\d+)\)?\s*percent",
        ],
        "retention_money": [
            r"rate of\s*(?:five|5)\s*\(?(\d+)\)?\s*percent.*?Retention Money",
            r"deduct at the rate of\s*(?:five|5)\s*\(?(\d+)\)?\s*percent",
            r"retention money.*?\(?(\d+)\)?\s*percent",
        ],
    }

    @staticmethod
    def _find_criteria(text: str, key: str) -> Optional[str]:
        """Try all patterns for a given criteria key."""
        flags = re.IGNORECASE | re.DOTALL
        for pattern in TDSCriteriaExtractor.PATTERNS.get(key, []):
            match = re.search(pattern, text, flags)
            if match:
                value = match.group(1).replace(",", "").strip()
                return value
        return None

    @staticmethod
    def extract_from_text(text: str) -> Dict[str, Any]:
        """Extract all criteria from raw TDS text."""
        criteria: Dict[str, Any] = {}
        for key in TDSCriteriaExtractor.PATTERNS:
            value = TDSCriteriaExtractor._find_criteria(text, key)
            if value:
                # Format with unit label
                if key in ("performance_security", "retention_money"):
                    criteria[key] = f"{value}%"
                elif key == "general_experience":
                    if not 1 <= int(value) <= 50:  # sanity: reject year-like captures
                        continue
                    criteria[key] = f"{value} years"
                elif key in ("specific_experience_count",):
                    criteria[key] = value
                else:
                    criteria[key] = f"Tk. {value} Lakh"
        return criteria

    @classmethod
    def extract_from_pdf(cls, pdf_path: str | Path) -> Dict[str, Any]:
        """Extract criteria from a TDS PDF file."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.warning("TDS PDF not found: %s", pdf_path)
            return {}

        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as exc:
            logger.warning("Failed to extract text from %s: %s", pdf_path, exc)
            return {}

        if not text.strip():
            logger.warning("No text extracted from TDS PDF: %s", pdf_path)
            return {}

        criteria = cls.extract_from_text(text)
        logger.info("TDS criteria extracted from %s: %d fields", pdf_path.name, len(criteria))
        return criteria

    @classmethod
    def extract_from_bytes(cls, content: bytes) -> Dict[str, Any]:
        """Extract criteria from PDF bytes (in-memory)."""
        import io
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as exc:
            logger.warning("Failed to extract text from PDF bytes: %s", exc)
            return {}
        return cls.extract_from_text(text)

    @classmethod
    def find_tds_pdf(cls, tender_dir: str | Path) -> Optional[Path]:
        """Search common TDS PDF locations under a tender directory."""
        tender_dir = Path(tender_dir)
        search_paths = [
            tender_dir / "docs" / "Section2_Tender Data Sheet",
            tender_dir / "docs" / "Section2",
            tender_dir / "Section2_Tender Data Sheet",
            tender_dir / "Section2",
            tender_dir,
        ]
        for sp in search_paths:
            if sp.is_dir():
                for pdf in sorted(sp.glob("*.pdf")):
                    lower = pdf.name.lower()
                    if any(k in lower for k in ("tds", "tender data", "data sheet", "section2")):
                        return pdf
                # Fall back to any PDF in the directory
                for pdf in sorted(sp.glob("*.pdf")):
                    return pdf
            elif sp.suffix == ".pdf" and sp.exists():
                return sp
        return None

    @classmethod
    def extract_for_tender(cls, tender_id: str, base_dir: str | Path = "uploads") -> Dict[str, Any]:
        """Convenience: find and extract TDS criteria for a given tender ID."""
        tender_dir = Path(base_dir) / str(tender_id)
        tds_pdf = cls.find_tds_pdf(tender_dir)
        if tds_pdf:
            return cls.extract_from_pdf(tds_pdf)
        logger.info("No TDS PDF found for tender %s in %s", tender_id, tender_dir)
        return {}


# ── Standalone CLI helper ───────────────────────────────────────────────────

def _cli():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.services.tds_extractor <pdf_path>")
        sys.exit(1)
    result = TDSCriteriaExtractor.extract_from_pdf(sys.argv[1])
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
