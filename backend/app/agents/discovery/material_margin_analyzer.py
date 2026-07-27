"""
Agent 049 - Material Margin Analyzer
Compares SOR schedule rates against market prices per item category.
Computes profit margin per item for bid optimization.
"""
from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging, json, uuid

logger = logging.getLogger(__name__)

MATERIAL_CATEGORIES = {
    "cement": ["cement", "portland", "concrete"],
    "steel": ["steel", "rod", "rebar", "ms rod", "deformed"],
    "brick": ["brick", "block", "boulder"],
    "sand": ["sand", "sylhet sand", "local sand"],
    "aggregate": ["aggregate", "stone", "chip", "gravel"],
    "pipe": ["pipe", "fittings", "upvc", "gi pipe"],
    "tile": ["tile", "ceramic", "vitrified"],
    "paint": ["paint", "enamel", "distemper", "emulsion"],
}

class MaterialMarginAnalyzerAgent(BaseAgent):
    agent_id = "agent-049-material-margin-analyzer"
    agent_name = "Material Margin Analyzer"
    description = "Compares SOR schedule rates vs market prices to compute item-wise profit margins"
    dependencies = ["agent-048-material-price-crawler"]
    version = "1.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        action = context.get("action", "analyze_margins")
        if action == "item_analysis":
            return await self._item_analysis(context)
        if action == "by_tender":
            return await self._by_tender(context)
        if action == "populate_rates":
            from app.services.rate_analysis_templates import populate_rate_analysis
            await populate_rate_analysis()
            return AgentResult(status=AgentStatus.SUCCESS, output={"message": "Rate analysis populated"})
        if action == "margin_breakdown":
            return await self._margin_with_breakdown(context)
        return await self._analyze_margins()

    # ── Aggregate margin analysis ────────────────────────────────────

    async def _analyze_margins(self) -> AgentResult:
        """Compute per-category/agency/zone margins across all SOR items."""
        from app.db.database import get_session
        from sqlalchemy import text

        await self._ensure_tables()
        results = {"categories": {}, "total_items": 0, "matched_items": 0, "errors": []}

        async with get_session() as session:
            # Get all SOR rates with zone data
            sor_rows = await session.execute(text("""
                SELECT id, agency, code, description, unit,
                       zone_a, zone_b, zone_c, zone_d
                FROM sor_rates
                WHERE is_active = true
                  AND (zone_a > 0 OR zone_b > 0 OR zone_c > 0 OR zone_d > 0)
                LIMIT 5000
            """))
            items = sor_rows.fetchall()

            # Get aggregate market prices per category/zone
            market_rows = await session.execute(text("""
                SELECT category, COALESCE(zone, '') as zone,
                       AVG(price_bdt) as avg_price,
                       COUNT(*) as sample_count
                FROM material_prices
                WHERE price_bdt > 0
                GROUP BY category, zone
            """))
            market_by_cat_zone = {}
            for r in market_rows.fetchall():
                key = f"{r.category}|{r.zone}"
                market_by_cat_zone[key] = {"avg": float(r.avg_price), "samples": r.sample_count}

            results["total_items"] = len(items)
            matched = 0

            for item in items:
                item_id, agency, code, desc, unit, za, zb, zc, zd = item
                if not desc:
                    continue
                category = self._classify_material(desc)
                if not category:
                    continue
                zones = {"A": za, "B": zb, "C": zc, "D": zd}
                for zone_label, zone_val in zones.items():
                    if not zone_val or float(zone_val) <= 0:
                        continue
                    sor_rate = float(zone_val)
                    mkt_key = f"{category}|{zone_label}"
                    mp = market_by_cat_zone.get(mkt_key)
                    if not mp:
                        continue
                    margin = round(sor_rate - mp["avg"], 2)
                    margin_pct = round((margin / mp["avg"]) * 100, 2) if mp["avg"] > 0 else 0.0

                    cat_key = f"{category}|{agency}|{zone_label}"
                    if cat_key not in results["categories"]:
                        results["categories"][cat_key] = {
                            "category": category, "agency": agency, "zone": zone_label,
                            "sor_rates": [], "market_avg": mp["avg"],
                            "total_margin": 0.0, "count": 0, "sample_count": mp["samples"],
                        }
                    cat = results["categories"][cat_key]
                    cat["sor_rates"].append(sor_rate)
                    cat["total_margin"] += margin
                    cat["count"] += 1
                    matched += 1

                    # Store detail row
                    try:
                        async with session.begin_nested():
                            await session.execute(text("""
                                INSERT INTO material_margins
                                    (id, material_category, agency, zone, sor_code,
                                     sor_description, sor_rate, avg_market_price,
                                     margin_bdt, margin_pct, unit, sample_count)
                                VALUES (:id, :cat, :agency, :zone, :code,
                                        :desc, :srate, :mkt,
                                        :margin, :margpct, :unit, :samples)
                                ON CONFLICT (sor_code, agency, zone) DO UPDATE
                                    SET margin_bdt = EXCLUDED.margin_bdt,
                                        margin_pct = EXCLUDED.margin_pct,
                                        computed_at = NOW()
                            """), {
                                "id": str(uuid.uuid4()), "cat": category,
                                "agency": agency, "zone": zone_label,
                                "code": code, "desc": desc[:300],
                                "srate": sor_rate, "mkt": mp["avg"],
                                "margin": margin, "margpct": margin_pct,
                                "unit": unit, "samples": mp["samples"],
                            })
                    except Exception as e:
                        logger.debug(f"Failed to store margin: {e}")

            results["matched_items"] = matched

            # Compute summaries per category
            for k, v in results["categories"].items():
                v["avg_sor_rate"] = round(sum(v["sor_rates"]) / len(v["sor_rates"]), 2) if v["sor_rates"] else 0
                v["avg_margin_bdt"] = round(v["total_margin"] / v["count"], 2) if v["count"] else 0
                v["avg_margin_pct"] = round((v["avg_margin_bdt"] / v["market_avg"]) * 100, 2) if v["market_avg"] > 0 else 0.0
                del v["sor_rates"]
                del v["total_margin"]

            await session.commit()

        summary = {k: f"{v['avg_margin_bdt']} BDT ({v['avg_margin_pct']}%)" for k, v in results["categories"].items()}
        await self.share_knowledge(
            entry_type="margin_analysis",
            tender_id="_market",
            data=results,
            summary=f"{results['matched_items']}/{results['total_items']} SOR items matched to prices, {len(results['categories'])} category-zone combos",
            tags=["margin", "material", "analysis"],
        )

        return AgentResult(status=AgentStatus.SUCCESS, output={
            "total_items": results["total_items"],
            "matched_items": results["matched_items"],
            "categories": len(results["categories"]),
            "sample_margins": {k: {"margin_bdt": v["avg_margin_bdt"], "margin_pct": v["avg_margin_pct"], "agency": v["agency"], "zone": v["zone"]}
                               for k, v in list(results["categories"].items())[:20]},
            "errors": results["errors"][:5],
        })

    # ── Item-level analysis ──────────────────────────────────────────

    async def _item_analysis(self, context: Dict[str, Any]) -> AgentResult:
        """Analyze margin for a specific SOR code/description."""
        from app.db.database import get_session
        from sqlalchemy import text

        sor_code = context.get("sor_code", "")
        agency = context.get("agency", "")
        zone = context.get("zone", "A")

        if not sor_code:
            return AgentResult(status=AgentStatus.FAILED, output={"error": "sor_code required"})

        async with get_session() as session:
            rows = await session.execute(text("""
                SELECT code, description, unit, zone_a, zone_b, zone_c, zone_d, agency
                FROM sor_rates
                WHERE code = :code AND (:agency = '' OR agency = :agency2)
                LIMIT 5
            """), {"code": sor_code, "agency": agency, "agency2": agency})
            items = rows.fetchall()

            results = []
            for item in items:
                code, desc, unit, za, zb, zc, zd, ag = item
                zmap = {"A": za, "B": zb, "C": zc, "D": zd}
                zone_rate = float(zmap.get(zone, za) or 0)
                category = self._classify_material(desc) if desc else ""

                mkt = await session.execute(text("""
                    SELECT AVG(price_bdt), COUNT(*)
                    FROM material_prices
                    WHERE category = :cat
                      AND (zone = :zone OR zone = '')
                      AND price_bdt > 0
                """), {"cat": category, "zone": zone})
                mkt_row = mkt.fetchone()
                mkt_avg = float(mkt_row[0]) if mkt_row and mkt_row[0] else 0
                mkt_count = mkt_row[1] if mkt_row else 0

                margin = round(zone_rate - mkt_avg, 2) if mkt_avg > 0 else 0
                margin_pct = round((margin / mkt_avg) * 100, 2) if mkt_avg > 0 else 0

                results.append({
                    "code": code, "description": desc[:200], "unit": unit,
                    "agency": ag, "zone": zone,
                    "sor_rate": zone_rate,
                    "avg_market_price": mkt_avg,
                    "margin_bdt": margin,
                    "margin_pct": margin_pct,
                    "market_samples": mkt_count,
                })

        return AgentResult(status=AgentStatus.SUCCESS, output={
            "results": results,
            "total": len(results),
        })

    # ── Tender BOQ margin analysis ───────────────────────────────────

    async def _by_tender(self, context: Dict[str, Any]) -> AgentResult:
        """Compute item-level margins for all BOQ items in a tender."""
        from app.db.database import get_session
        from sqlalchemy import text

        tender_id = context.get("tender_id", "")
        agency = context.get("agency", "")
        zone = context.get("zone", "A")

        if not tender_id:
            return AgentResult(status=AgentStatus.FAILED, output={"error": "tender_id required"})

        # Look up BOQ items from knowledge
        boq_data = await self.query_brain("boq_text", str(tender_id))
        if not boq_data:
            # Try boq_items table
            pass

        async with get_session() as session:
            boq_rows = await session.execute(text("""
                SELECT item_no, description, unit, quantity, rate, amount
                FROM boq_items
                WHERE tender_id = :tid
                ORDER BY item_no
            """), {"tid": str(tender_id)})
            items = boq_rows.fetchall()

            if not items:
                return AgentResult(status=AgentStatus.SUCCESS, output={
                    "tender_id": tender_id,
                    "total_items": 0,
                    "message": "No BOQ items found for this tender. Parse the BOQ PDF first.",
                })

            results = []
            total_profit = 0.0
            total_sor_amount = 0.0
            total_market_amount = 0.0

            for item in items:
                item_no, desc, unit, qty, rate, amount = item
                category = self._classify_material(desc) if desc else ""
                if not category:
                    continue

                mkt = await session.execute(text("""
                    SELECT AVG(price_bdt), COUNT(*)
                    FROM material_prices
                    WHERE category = :cat
                      AND (zone = :zone OR zone = '')
                      AND price_bdt > 0
                """), {"cat": category, "zone": zone})
                mkt_row = mkt.fetchone()
                mkt_avg = float(mkt_row[0]) if mkt_row and mkt_row[0] else 0
                mkt_count = mkt_row[1] if mkt_row else 0

                sor_rate = float(rate or 0)
                unit_margin = round(sor_rate - mkt_avg, 2) if mkt_avg > 0 else 0
                margin_pct = round((unit_margin / mkt_avg) * 100, 2) if mkt_avg > 0 else 0
                qty_f = float(qty or 0)

                item_profit = round(unit_margin * qty_f, 2)
                item_sor_amount = round(sor_rate * qty_f, 2)
                item_market_amount = round(mkt_avg * qty_f, 2)

                total_profit += item_profit
                total_sor_amount += item_sor_amount
                total_market_amount += item_market_amount

                results.append({
                    "item_no": item_no, "description": desc[:200],
                    "unit": unit, "quantity": qty_f,
                    "sor_rate": sor_rate,
                    "avg_market_price": mkt_avg,
                    "unit_margin": unit_margin,
                    "margin_pct": margin_pct,
                    "sor_amount": item_sor_amount,
                    "market_amount": item_market_amount,
                    "profit": item_profit,
                    "market_samples": mkt_count,
                })

            overall_margin_pct = round((total_profit / total_market_amount) * 100, 2) if total_market_amount > 0 else 0

            await self.share_knowledge(
                entry_type="tender_margin_analysis",
                tender_id=str(tender_id),
                data={"items": results, "summary": {
                    "total_items": len(results),
                    "total_sor_amount": total_sor_amount,
                    "total_market_amount": total_market_amount,
                    "total_profit": total_profit,
                    "overall_margin_pct": overall_margin_pct,
                }},
                summary=f"Tender {tender_id}: {total_profit} BDT profit on {total_sor_amount} BDT SOR estimate ({overall_margin_pct}% margin)",
                tags=["margin", "boq", "tender"],
            )

            return AgentResult(status=AgentStatus.SUCCESS, output={
                "tender_id": tender_id,
                "total_items": len(results),
                "total_sor_amount": total_sor_amount,
                "total_market_amount": total_market_amount,
                "total_profit": total_profit,
                "overall_margin_pct": overall_margin_pct,
                "items": results[:50],
            })

    # ── Rate analysis margin breakdown ───────────────────────────────

    async def _margin_with_breakdown(self, context: Dict[str, Any]) -> AgentResult:
        """Compute margin for a SOR item using rate analysis composition."""
        from app.db.database import get_session
        from sqlalchemy import text
        from app.services.rate_analysis_templates import get_composition, ensure_rate_analysis_table

        sor_code = context.get("sor_code", "")
        agency = context.get("agency", "BWDB")
        zone = context.get("zone", "A")

        if not sor_code:
            return AgentResult(status=AgentStatus.FAILED, output={"error": "sor_code required"})

        await ensure_rate_analysis_table()
        composition = get_composition(sor_code)

        async with get_session() as session:
            # Get SOR rate (use LIKE for code suffix matching)
            sor_row = await session.execute(text("""
                SELECT description, unit, zone_a, zone_b, zone_c, zone_d
                FROM sor_rates
                WHERE code LIKE :pattern AND agency = :agency
                LIMIT 1
            """), {"pattern": sor_code + "%", "agency": agency})
            sor = sor_row.fetchone()
            if not sor:
                return AgentResult(status=AgentStatus.FAILED, output={"error": f"SOR code {sor_code} not found for {agency}"})

            desc, unit, za, zb, zc, zd = sor
            zmap = {"A": za, "B": zb, "C": zc, "D": zd}
            sor_rate = float(zmap.get(zone, za) or 0)

            if not composition:
                return AgentResult(status=AgentStatus.SUCCESS, output={
                    "sor_code": sor_code, "description": desc,
                    "sor_rate": sor_rate, "unit": unit,
                    "message": "No rate analysis template for this code. Add to rate_analysis_templates.py",
                })

            # Build breakdown with market prices
            breakdown = []
            total_material_cost = 0.0
            total_labor_cost = 0.0
            total_equipment_cost = 0.0

            for sub in composition:
                sub_cost = 0.0
                market_price = 0.0
                market_samples = 0

                # Look up market price for material sub-items
                if sub["component"] == "material" and sub.get("mat_cat"):
                    mkt = await session.execute(text("""
                        SELECT AVG(price_bdt), COUNT(*)
                        FROM material_prices
                        WHERE category = :cat
                          AND (zone = :zone OR zone = '')
                          AND price_bdt > 0
                    """), {"cat": sub["mat_cat"], "zone": zone})
                    mkt_row = mkt.fetchone()
                    if mkt_row and mkt_row[0]:
                        market_price = float(mkt_row[0])
                        market_samples = mkt_row[1]
                        sub_cost = round(market_price * sub["qty"], 2)
                        total_material_cost += sub_cost
                elif sub["component"] == "labor":
                    # Use standard labor rate (Tk 600 skilled, Tk 400 unskilled)
                    labor_rate = 600.0 if "skilled" in sub["sub_desc"].lower().split() else 400.0
                    sub_cost = round(labor_rate * sub["qty"], 2)
                    total_labor_cost += sub_cost
                    market_price = labor_rate
                elif sub["component"] == "equipment":
                    # Use standard equipment rate (varies by type)
                    equip_rate = self._estimate_equip_rate(sub["sub_desc"])
                    sub_cost = round(equip_rate * sub["qty"], 2)
                    total_equipment_cost += sub_cost
                    market_price = equip_rate

                breakdown.append({
                    "sub_item": sub["sub_desc"],
                    "unit": sub["unit"],
                    "quantity": sub["qty"],
                    "component": sub["component"],
                    "category": sub.get("mat_cat", ""),
                    "unit_price": market_price,
                    "total_cost": sub_cost,
                    "market_samples": market_samples,
                })

            # Compute margin
            total_cost = total_material_cost + total_labor_cost + total_equipment_cost
            profit_bdt = round(sor_rate - total_cost, 2)
            profit_pct = round((profit_bdt / total_cost) * 100, 2) if total_cost > 0 else 0

            return AgentResult(status=AgentStatus.SUCCESS, output={
                "sor_code": sor_code,
                "description": desc[:200],
                "unit": unit,
                "agency": agency,
                "zone": zone,
                "sor_rate": sor_rate,
                "breakdown": breakdown,
                "total_material_cost": round(total_material_cost, 2),
                "total_labor_cost": round(total_labor_cost, 2),
                "total_equipment_cost": round(total_equipment_cost, 2),
                "total_cost": round(total_cost, 2),
                "profit_bdt": profit_bdt,
                "profit_pct": profit_pct,
            })

    @staticmethod
    def _estimate_equip_rate(desc: str) -> float:
        d = desc.lower()
        if "excavator" in d or "dozer" in d or "backhoe" in d: return 2500.0
        if "crane" in d: return 3000.0
        if "roller" in d or "compactor" in d: return 2000.0
        if "mixer" in d: return 800.0
        if "vibrator" in d: return 400.0
        if "pump" in d or "dewatering" in d: return 1200.0
        if "pile" in d or "rig" in d or "hammer" in d: return 5000.0
        if "paver" in d or "plant" in d: return 3500.0
        if "boat" in d: return 1500.0
        if "scaffold" in d: return 200.0
        return 1000.0

    # ── Helpers ──────────────────────────────────────────────────────

    def _classify_material(self, description: str) -> str:
        text = description.lower()
        for cat, keywords in MATERIAL_CATEGORIES.items():
            if any(kw in text for kw in keywords):
                return cat
        return ""

    async def _ensure_tables(self):
        from app.db.database import get_engine
        from sqlalchemy import text
        e = get_engine()
        async with e.connect() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS material_margins (
                    id UUID PRIMARY KEY,
                    material_category VARCHAR(100) NOT NULL,
                    agency VARCHAR(20) NOT NULL,
                    zone VARCHAR(10) NOT NULL,
                    sor_code VARCHAR(100),
                    sor_description TEXT,
                    sor_rate DECIMAL(15,2),
                    avg_market_price DECIMAL(15,2),
                    margin_bdt DECIMAL(15,2),
                    margin_pct DECIMAL(8,2),
                    unit VARCHAR(50),
                    sample_count INT DEFAULT 0,
                    computed_at TIMESTAMP DEFAULT NOW()
                )
            """))
            await conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_margin_code_agency_zone
                ON material_margins(sor_code, agency, zone)
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_margin_category
                ON material_margins(material_category, agency, zone)
            """))
            await conn.commit()
        logger.info("material_margins table ready")
