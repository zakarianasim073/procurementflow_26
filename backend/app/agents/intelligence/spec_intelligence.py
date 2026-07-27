"""
Agent 6 — Specification Intelligence Agent
Reads technical specifications (TDS), extracts requirements, flags risks and special materials.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Dict, List

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.services.tds_extractor import TDSCriteriaExtractor

logger = logging.getLogger(__name__)


class SpecIntelligenceAgent(BaseAgent):
    agent_id = "agent-006-spec-intelligence"
    agent_name = "Specification Intelligence Agent"
    description = "Analyzes technical specifications from TDS to extract requirements, risks, special materials, and financial qualification criteria."
    dependencies: List[str] = ["agent-004-document-ai"]
    version = "2.1.0"

    @staticmethod
    def _amount_bdt(value: Any) -> float:
        """Parse e-GP criteria amounts such as 'Tk. 40.00 Lakh' into BDT."""
        if isinstance(value, (int, float)):
            return float(value)
        text_value = str(value or "").replace(",", "")
        match = re.search(r"(\d+(?:\.\d+)?)", text_value)
        if not match:
            return 0.0
        amount = float(match.group(1))
        lowered = text_value.lower()
        if "crore" in lowered or re.search(r"\bcr\b", lowered):
            amount *= 10_000_000
        elif "lakh" in lowered or "lac" in lowered:
            amount *= 100_000
        elif "thousand" in lowered:
            amount *= 1_000
        return amount

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_id = context.get("tender_id", "eGP-001")
        specs_path = context.get("specifications_path", "")
        upstream = context.get("upstream", {})
        acquisition = upstream.get("agent-002-tender-acquisition", {})
        documents = acquisition.get("documents", {})

        if not specs_path:
            file_paths = context.get("file_paths") or {}
            if isinstance(file_paths, dict):
                specs_path = (
                    file_paths.get("specifications")
                    or file_paths.get("tds")
                    or file_paths.get("tds_2")
                    or ""
                )
        if not specs_path and isinstance(documents, dict):
            specs_path = (
                documents.get("Specifications")
                or documents.get("specifications")
                or documents.get("TDS")
                or documents.get("tds")
                or ""
            )
        if not specs_path and isinstance(documents, list):
            for item in documents:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("doc_type") or item.get("type") or item.get("name") or "").lower()
                if "spec" in label or "tds" in label:
                    specs_path = str(item.get("path") or item.get("file_path") or "")
                    break

        # Extract text from TDS PDF if available
        spec_text = await asyncio.to_thread(self._extract_spec_text, specs_path)

        requirements = self._extract_requirements(spec_text)
        risks = self._analyze_risks(requirements, spec_text)
        special_materials = self._identify_special_materials(requirements, spec_text)

        # Extract financial qualification criteria from TDS
        financial_criteria = {}
        if spec_text:
            financial_criteria = TDSCriteriaExtractor.extract_from_text(spec_text)
        if not financial_criteria:
            persisted = context.get("persisted_tds_criteria")
            if isinstance(persisted, dict) and persisted:
                financial_criteria = persisted
        if not financial_criteria and self.brain:
            # Local tender-manager files may be placeholders while acquisition
            # already persisted an authoritative TDS extraction. Reuse the
            # structured criteria with a bounded lookup instead of re-querying
            # the large raw tds_text entry.
            try:
                criteria_entries = await asyncio.wait_for(
                    self.query_brain("tds_criteria", tender_id),
                    timeout=5.0,
                )
                for entry in criteria_entries:
                    data = entry.get("data", {}) if isinstance(entry, dict) else {}
                    data = data.get("payload", data) if isinstance(data, dict) else {}
                    if isinstance(data, dict) and data:
                        financial_criteria = data
                        break
            except asyncio.TimeoutError:
                logger.warning("Bounded tds_criteria lookup timed out for %s", tender_id)
        if not financial_criteria and not spec_text:
            # Try to find TDS PDF from brain or documents
            tds_pdf = TDSCriteriaExtractor.find_tds_pdf(f"uploads/{tender_id}")
            if tds_pdf:
                financial_criteria = TDSCriteriaExtractor.extract_from_pdf(tds_pdf)
            else:
                # Try brain knowledge
                brain_entries = await self.query_brain("tds_text", tender_id)
                if brain_entries:
                    for entry in brain_entries:
                        data = entry.get("data", {})
                        text = data.get("text", "")
                        if text:
                            financial_criteria = TDSCriteriaExtractor.extract_from_text(text)
                            if financial_criteria:
                                break

        if not requirements and not spec_text:
            requirements, risks, special_materials = await self._try_brain_tds(tender_id, spec_text)

        if not requirements and not spec_text:
            requirements, risks, special_materials = self._get_demo_data(tender_id)

        output = {
            "tender_id": tender_id,
            "requirements_count": len(requirements),
            "requirements": requirements,
            "risks": risks,
            "risks_count": len(risks),
            "special_materials": special_materials,
            "special_materials_count": len(special_materials),
            "financial_criteria": financial_criteria,
            "financial_criteria_count": len(financial_criteria),
        }

        # Share financial criteria with brain for downstream agents
        if financial_criteria and self.brain:
            await self.share_knowledge(
                entry_type="tds_criteria",
                tender_id=tender_id,
                data=financial_criteria,
                summary=f"Financial criteria extracted for {tender_id}",
                tags=["tds", "financial_criteria", "qualification"],
            )
            await self.share_knowledge(
                entry_type="tender_requirement_enrichment",
                tender_id=tender_id,
                data={
                    "tender_security_amount_bdt": self._amount_bdt(financial_criteria.get("tender_security")),
                    "tender_security_text": financial_criteria.get("tender_security"),
                    "general_experience": financial_criteria.get("general_experience"),
                    "specific_experience_value_bdt": self._amount_bdt(financial_criteria.get("specific_experience_value")),
                    "specific_experience_count": financial_criteria.get("specific_experience_count"),
                    "avg_annual_turnover_bdt": self._amount_bdt(financial_criteria.get("avg_annual_turnover")),
                    "liquid_assets_bdt": self._amount_bdt(financial_criteria.get("liquid_assets")),
                    "min_tender_capacity_bdt": self._amount_bdt(financial_criteria.get("min_tender_capacity")),
                    "performance_security": financial_criteria.get("performance_security"),
                    "retention_money": financial_criteria.get("retention_money"),
                    "evidence": {
                        "document_type": "TDS",
                        "source_entry_type": "tds_text",
                        "extractor": self.agent_id,
                    },
                },
                summary=f"Evidence-backed tender security and eligibility for {tender_id}",
                tags=["tds", "eligibility", "tender_security", "works_only"],
            )

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=output,
        )

    def _extract_spec_text(self, path: str) -> str:
        """Extract text from a specification/TDS PDF."""
        if not path or not os.path.isfile(path):
            return ""
        try:
            import fitz
            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return text
        except Exception as e:
            logger.debug(f"Could not read spec PDF: {e}")
            return ""

    def _extract_requirements(self, text: str) -> List[str]:
        """Extract technical requirements from TDS text."""
        if not text:
            return []

        requirements = []

        # Experience/qualification requirements
        for pattern in [
            r'(Experience Criteria.*?)(?:\n\n|\d+\.)',
            r'(Qualification Requirements.*?)(?:\n\n|\d+\.)',
            r'(Personnel Requirements.*?)(?:\n\n|\d+\.)',
            r'(Key Personnel.*?)(?:\n\n|\d+\.)',
        ]:
            m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if m:
                requirements.append(m.group(1).strip())

        # Individual requirement lines
        req_patterns = [
            r'minimum\s+(\d+)\s+years?\s+(?:of\s+)?(?:general\s+)?experience',
            r'should\s+have\s+(?:completed|executed)\s+(?:at\s+least\s+)?(\d+)\s+(?:similar|comparable)',
            r'minimum\s+annual\s+(?:turnover|construction)\s+(?:value|turnover)\s+(?:of\s+)?[\u09F3Tk]?\s*([\d,]+)',
        ]
        for p in req_patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                requirements.append(m.group(0).strip())

        # Personnel requirements from TDS tables
        person_matches = re.findall(r'([A-Za-z\s]+?)\s*-\s*(\d+)\s*Nos?\s*.*?(\d+)\s*years?', text, re.IGNORECASE)
        for title, count, exp in person_matches:
            requirements.append(f"{title.strip()} - {count} Nos, {exp} years experience")

        return requirements

    def _analyze_risks(self, requirements: List[str], spec_text: str) -> List[str]:
        """Identify risks from requirements and specification text."""
        risks = []

        combined = " ".join(requirements) + " " + (spec_text or "")

        risk_indicators = {
            "asphalt": "Special Asphalt Grade Required",
            "bituminous": "Bituminous Material Required",
            "imported": "Imported Material Required — potential supply chain risk",
            "high performance": "Premium Performance Material Required",
            "specialist": "Specialist Subcontractor Required",
            "geotextile": "Special Geo-textile Material Required (97% Polypropylene)",
            "dredging": "Dredging Works — environmental compliance risk",
            "river": "River Works — seasonal/work window constraints",
        }

        for keyword, risk in risk_indicators.items():
            if keyword in combined.lower():
                risks.append(risk)

        return risks

    def _identify_special_materials(self, requirements: List[str], spec_text: str) -> List[str]:
        """Identify special materials required from specifications."""
        specials = []
        combined = " ".join(requirements) + " " + (spec_text or "")

        material_indicators = {
            "geotextile": "Geo-textile Fabric (97% Polypropylene, >=400gm/m²)",
            "asphalt": "Asphalt Concrete (Hot Mix)",
            "polypropylene": "Polypropylene Geo-textile Bags",
            "cc block": "Cement Concrete Blocks (45x45x45 cm, 35x35x35 cm)",
            "stone": "Stone Chips (40mm downgraded)",
            "grade 60": "Grade 60W Reinforcement Steel",
            "total station": "Total Station Survey Equipment",
            "barge": "Barge / Bulkhead Dredger",
        }

        for keyword, material in material_indicators.items():
            if keyword.lower() in combined.lower():
                if material not in specials:
                    specials.append(material)

        return specials

    async def _try_brain_tds(self, tender_id: str, spec_text: str) -> tuple:
        """Try to get TDS data from brain knowledge store."""
        try:
            entries = await self.query_brain("tds_text", tender_id)
            if entries:
                for entry in entries:
                    data = entry.get("data", {})
                    text = data.get("text", "") or data.get("content", "") or str(data)
                    if len(text) > 200:
                        reqs = self._extract_requirements(text)
                        if reqs:
                            risks = self._analyze_risks(reqs, text)
                            materials = self._identify_special_materials(reqs, text)
                            return reqs, risks, materials
        except Exception as e:
            logger.debug(f"Brain TDS lookup failed: {e}")
        return [], [], []

    def _get_demo_data(self, tender_id: str) -> tuple:
        """Return empty — no mock data. Real spec data comes from TDS PDF or brain knowledge."""
        return [], [], []
