"""
Agent 048 - Material Price Crawler
Crawls real Bangladeshi construction material seller websites every 7 days.
Collects prices for cement, steel, brick, sand, aggregate, etc.
Provides data for NPPI computation per zone per agency (every 28 days).
"""
from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta, date
from dataclasses import dataclass, field
import logging, json, uuid, re, hashlib, math

logger = logging.getLogger(__name__)

CRAWL_INTERVAL_DAYS = 7
NPPI_INTERVAL_DAYS = 28

@dataclass
class MaterialPrice:
    material_name: str
    category: str
    price_bdt: float
    unit: str
    seller: str
    source_url: str
    division: str = ""
    zone: str = ""
    currency: str = "BDT"
    collected_at: datetime = None

class MaterialPriceCrawlerAgent(BaseAgent):
    agent_id = "agent-048-material-price-crawler"
    agent_name = "Material Price Crawler"
    description = "Crawls BD construction material prices from real seller websites every 7 days"
    dependencies = []
    version = "1.0.0"

    # ── Crawl targets: real BD construction material sources ──────────
    BROWSER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    TARGETS = [
        {
            "name": "daraz_construction",
            "url": "https://www.daraz.com.bd/construction-tools/",
            "parser": "_parse_generic_listing",
        },
        {
            "name": "ajkerdeal_construction",
            "url": "https://www.ajkerdeal.com/construction",
            "parser": "_parse_generic_listing",
        },
        {
            "name": "priyoshop_construction",
            "url": "https://www.priyoshop.com/construction-materials",
            "parser": "_parse_generic_listing",
        },
    ]

    MATERIAL_CATEGORIES = {
        "cement": ["cement", "portland", "concrete", "mortar", "grout"],
        "steel": ["steel", "rod", "rebar", "ms rod", "deformed", "reinforcement", "mild steel"],
        "brick": ["brick", "block", "boulder", "brick flat", "brick work"],
        "sand": ["sand", "sylhet sand", "local sand", "silt", "fine aggregate"],
        "aggregate": ["aggregate", "stone", "chip", "gravel", "brick chips", "coarse aggregate"],
        "pipe": ["pipe", "fittings", "upvc", "gi pipe", "hume pipe", "drain"],
        "tile": ["tile", "ceramic", "vitrified", "flooring"],
        "paint": ["paint", "enamel", "distemper", "emulsion", "varnish"],
        "wood": ["wood", "timber", "plank", "plywood"],
        "geotextile": ["geotextile", "geobag", "geobags", "geo bag", "woven bag"],
        "bitumen": ["bitumen", "asphalt", "emulsion", "pitch"],
        "waterproofing": ["waterproof", "damp proof", "membrane"],
    }

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        action = context.get("action", "crawl_all")

        if action == "compute_nppi":
            return await self._compute_nppi()
        if action == "crawl_prices":
            return await self._crawl_all_targets()
        if action == "crawl_and_nppi":
            prices = await self._crawl_all_targets()
            nppi = await self._compute_nppi()
            return AgentResult(status=AgentStatus.SUCCESS, output={
                "crawl": prices.output if hasattr(prices, 'output') else prices,
                "nppi": nppi.output if hasattr(nppi, 'output') else nppi,
            })

        return await self._crawl_all_targets()

    # ── Main crawl loop ──────────────────────────────────────────────

    async def _crawl_all_targets(self) -> AgentResult:
        from bs4 import BeautifulSoup
        import httpx

        results = {"targets_attempted": 0, "targets_ok": 0, "prices_collected": 0, "prices": [], "errors": []}

        for target in self.TARGETS:
            results["targets_attempted"] += 1
            try:
                async with httpx.AsyncClient(verify=False, timeout=20, follow_redirects=True) as client:
                    resp = await client.get(target["url"], headers=self.BROWSER_HEADERS)
                    if resp.status_code != 200:
                        results["errors"].append(f"{target['name']}: HTTP {resp.status_code}")
                        continue

                    soup = BeautifulSoup(resp.text, "lxml")
                    parser = getattr(self, target["parser"], None)
                    if parser:
                        items = parser(soup, target["url"])
                        for item in items:
                            item.collected_at = datetime.now(timezone.utc)
                            results["prices"].append(item)
                        results["targets_ok"] += 1
                        logger.info(f"{target['name']}: {len(items)} prices collected")
                    else:
                        results["errors"].append(f"{target['name']}: no parser found")

            except Exception as e:
                logger.warning(f"Crawl failed for {target['name']}: {e}")
                results["errors"].append(f"{target['name']}: {str(e)[:100]}")

        results["prices_collected"] = len(results["prices"])

        # Always run SOR fallback to guarantee classified material prices
        sor_prices = await self._extract_sor_material_prices()
        existing_sellers = set(p.seller for p in results["prices"])
        for sp in sor_prices:
            if sp.seller not in existing_sellers:
                results["prices"].append(sp)
        results["prices_collected"] = len(results["prices"])
        if sor_prices:
            results["sor_fallback"] = len(sor_prices)

        # Persist to DB
        if results["prices"]:
            success = await self._store_prices(results["prices"])
            results["stored"] = success

        # Broadcast summary
        await self.share_knowledge(
            entry_type="material_price_crawl",
            tender_id="_market",
            data={"collected": results["prices_collected"], "errors": results["errors"]},
            summary=f"{results['prices_collected']} material prices from {results['targets_ok']}/{results['targets_attempted']} sources",
            tags=["material_prices", "crawl", "nppi"],
        )

        return AgentResult(status=AgentStatus.SUCCESS, output={
            "prices_collected": results["prices_collected"],
            "targets_ok": results["targets_ok"],
            "targets_total": results["targets_attempted"],
            "stored": results.get("stored", 0),
            "sor_fallback": results.get("sor_fallback", 0),
            "sample_prices": [{"material": p.material_name, "price": p.price_bdt, "seller": p.seller, "unit": p.unit, "category": p.category} for p in results["prices"][:20]],
            "errors": results["errors"][:5],
        })

    # ── Parsers: real BD e-commerce sites ────────────────────────────

    def _parse_ajkerdeal(self, soup, base_url: str) -> List[MaterialPrice]:
        """Parse product listings from ajkerdeal.com."""
        items = []
        seen = set()
        cards = soup.select("div.product-card, div.product-item, div.item, div[class*='product']")
        if not cards:
            cards = soup.select("a[href*='/product/'], a[href*='/item/']")

        for card in cards[:40]:
            try:
                title = self._extract_text(card, "h2, h3, h4, .product-name, .product-title, img[alt]")
                if not title:
                    continue
                price_text = self._extract_text(card, ".product-price, .price, .sale-price, span[class*='price'], .current-price")
                if not price_text:
                    continue
                price_bdt = self._extract_bdt(price_text)
                if price_bdt <= 0:
                    continue
                category, unit = self._classify_material(title, "")
                if not category:
                    continue
                dedup_key = f"{title.lower().strip()}|{price_bdt}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                href = self._extract_href(card)
                url = href if href.startswith("http") else f"https://www.ajkerdeal.com{href}" if href.startswith("/") else base_url
                seller = self._extract_text(card, ".seller-name, .shop-name, .vendor, .store-name") or "ajkerdeal.com"
                items.append(MaterialPrice(material_name=title[:200], category=category, price_bdt=price_bdt, unit=unit or "unit", seller=seller[:100], source_url=url))
            except Exception:
                continue
        return items

    def _parse_generic_listing(self, soup, base_url: str) -> List[MaterialPrice]:
        """Generic parser for any product listing page."""
        items = []
        seen = set()
        cards = soup.select("div[class*='product'], div[class*='item'], li[class*='product'], div[class*='card']")
        if not cards:
            cards = soup.find_all("a", href=re.compile(r"/product/|/item/|/p/"))
        for card in cards[:40]:
            try:
                title = self._extract_text(card, "h2, h3, h4, .name, .title, img[alt], a[title]")
                if not title:
                    continue
                price_text = self._extract_text(card, ".price, .sale-price, .current-price, span[class*='price'], .offer-price")
                if not price_text:
                    price_text = self._extract_text(card, "b, strong, .price-tag")
                if not price_text:
                    continue
                price_bdt = self._extract_bdt(price_text)
                if price_bdt <= 0:
                    continue
                category, unit = self._classify_material(title, "")
                if not category:
                    continue
                dedup_key = f"{title.lower().strip()}|{price_bdt}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                href = self._extract_href(card)
                url = href if href.startswith("http") else f"{base_url.rstrip('/')}{href}" if href.startswith("/") else base_url
                items.append(MaterialPrice(material_name=title[:200], category=category, price_bdt=price_bdt, unit=unit or "unit", seller="online_marketplace", source_url=url))
            except Exception:
                continue
        return items

    def _parse_chaldal(self, soup, base_url: str) -> List[MaterialPrice]:
        """Parse chaldal.com product listings."""
        items = []
        seen = set()
        for card in soup.select("div[class*='product'], div[class*='item'], div[data-testid*='product'], div[class*='card']")[:40]:
            try:
                title = self._extract_text(card, "h2, h3, h4, span[class*='name'], .product-name, .ProductName, img[alt]")
                if not title:
                    continue
                price_text = self._extract_text(card, ".price, .discounted-price, .ProductPrice, span[class*='price'], .current-price, .sale-price")
                if not price_text:
                    continue
                price_bdt = self._extract_bdt(price_text)
                if price_bdt <= 0:
                    continue
                category, unit = self._classify_material(title, "")
                if not category:
                    continue
                dedup_key = f"{title.lower().strip()}|{price_bdt}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                href = self._extract_href(card)
                url = href if href.startswith("http") else f"https://chaldal.com{href}" if href.startswith("/") else base_url
                items.append(MaterialPrice(material_name=title[:200], category=category, price_bdt=price_bdt, unit=unit or "unit", seller="chaldal.com", source_url=url))
            except Exception:
                continue
        return items

    @staticmethod
    def _extract_text(card, selector: str) -> str:
        el = card.select_one(selector) if hasattr(card, 'select_one') else None
        if el:
            return el.get("title") or el.get("alt") or el.get_text(strip=True) or ""
        return ""

    @staticmethod
    def _extract_href(card) -> str:
        a = card.select_one("a[href]") if hasattr(card, 'select_one') else None
        return a.get("href", "") if a else ""

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_bdt(text: str) -> float:
        """Extract BDT price from text like 'Tk 1,250', '৳850', 'BDT 1,200.00'."""
        text = text.replace(",", "").replace("৳", "").replace("Tk", "").replace("BDT", "").replace("tk", "").strip()
        nums = re.findall(r"(\d+(?:\.\d+)?)", text)
        return float(nums[0]) if nums else 0.0

    def _classify_material(self, title: str, desc: str) -> tuple:
        """Classify material into category and detect unit."""
        text = (title + " " + desc).lower()

        for cat, keywords in self.MATERIAL_CATEGORIES.items():
            if any(kw in text for kw in keywords):
                unit = self._detect_unit(text)
                return cat, unit

        for cat in list(self.MATERIAL_CATEGORIES.keys()):
            words = text.split()
            for w in words:
                for kw in self.MATERIAL_CATEGORIES[cat]:
                    if w.startswith(kw[:3]) and len(w) > 2:
                        unit = self._detect_unit(text)
                        return cat, unit

        return "", "unit"

    @staticmethod
    def _detect_unit(text: str) -> str:
        if any(u in text for u in ["per ton", "/ton", "tonne", "per tonne"]):
            return "ton"
        if any(u in text for u in ["per kg", "/kg", "per kilogram"]):
            return "kg"
        if any(u in text for u in ["per cft", "/cft", "cubic feet"]):
            return "cft"
        if any(u in text for u in ["per pcs", "/pcs", "per piece", "each"]):
            return "pcs"
        if any(u in text for u in ["per bag", "/bag", "per sack"]):
            return "bag"
        if "per sqft" in text or "/sqft" in text:
            return "sqft"
        return "unit"

    # ── SOR fallback: extract material rates from DB ────────────────

    async def _extract_sor_material_prices(self) -> List[MaterialPrice]:
        """Fallback: extract material unit rates from SOR data as baseline prices."""
        from app.db.database import get_session
        from sqlalchemy import text

        prices = []
        seen_rates = set()
        now = datetime.now(timezone.utc)

        try:
            async with get_session() as session:
                rows = await session.execute(text("""
                    SELECT description, zone_a, zone_b, zone_c, zone_d, agency, code
                    FROM sor_rates
                    WHERE zone_a IS NOT NULL AND zone_a > 0
                    LIMIT 500
                """))
                for row in rows.fetchall():
                    desc, za, zb, zc, zd, agency, code = row
                    if not desc:
                        continue
                    category, unit = self._classify_material(desc, "")
                    if not category:
                        continue
                    for zone_label, zone_val in [("A", za), ("B", zb), ("C", zc), ("D", zd)]:
                        if not zone_val or float(zone_val) <= 0:
                            continue
                        dedup = f"{agency}|{zone_label}|{category}|{float(zone_val):.2f}"
                        if dedup in seen_rates:
                            continue
                        seen_rates.add(dedup)
                        prices.append(MaterialPrice(
                            material_name=f"{desc[:150]} ({agency} SOR)",
                            category=category,
                            price_bdt=float(zone_val),
                            unit=unit or "unit",
                            seller=f"{agency}_SOR",
                            source_url="",
                            zone=zone_label,
                            division="",
                            collected_at=now,
                        ))
            logger.info(f"SOR fallback: {len(prices)} material prices extracted")
        except Exception as e:
            logger.warning(f"SOR fallback failed: {e}")
        return prices

    @staticmethod
    def _assign_zone(seller: str) -> str:
        """Guess zone from seller text (simplified)."""
        seller_lower = seller.lower()
        if any(c in seller_lower for c in ["dhaka", "narayanganj", "gazipur", "mymensingh"]):
            return "A"
        if any(c in seller_lower for c in ["chattogram", "sylhet", "cox", "bandarban"]):
            return "B"
        if any(c in seller_lower for c in ["khulna", "barishal", "barisal", "satkhira", "bagerhat"]):
            return "C"
        if any(c in seller_lower for c in ["rajshahi", "rangpur", "pabna", "bogra"]):
            return "D"
        return ""

    # ── DB storage ───────────────────────────────────────────────────

    async def _store_prices(self, prices: List[MaterialPrice]):
        """Persist collected prices to material_prices table."""
        from app.db.database import get_session
        from sqlalchemy import text

        await self._ensure_table()
        now = datetime.now(timezone.utc)

        async with get_session() as session:
            stored = 0
            for p in prices:
                try:
                    zone = self._assign_zone(p.seller) or p.zone
                    async with session.begin_nested():
                        await session.execute(
                            text("""
                                INSERT INTO material_prices 
                                    (id, material_name, category, price_bdt, unit, seller,
                                     source_url, zone, division, currency, collected_at, created_at)
                                VALUES (:id, :name, :cat, :price, :unit, :seller,
                                        :url, :zone, :div, :curr, :collected, :now)
                            """),
                            {
                                "id": str(uuid.uuid4()),
                                "name": p.material_name,
                                "cat": p.category,
                                "price": p.price_bdt,
                                "unit": p.unit,
                                "seller": p.seller,
                                "url": p.source_url,
                                "zone": zone,
                                "div": p.division,
                                "curr": p.currency,
                                "collected": p.collected_at,
                                "now": now,
                            }
                        )
                    stored += 1
                except Exception as e:
                    logger.debug(f"Failed to store price: {e}")
            if stored > 0:
                await session.commit()
                logger.info(f"Stored {stored}/{len(prices)} material prices to DB")
            return stored

    async def _ensure_table(self):
        """Create material_prices table if not exists."""
        from app.db.database import get_engine
        from sqlalchemy import text

        e = get_engine()
        async with e.connect() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS material_prices (
                    id UUID PRIMARY KEY,
                    material_name VARCHAR(300) NOT NULL,
                    category VARCHAR(100),
                    price_bdt DECIMAL(15,2),
                    unit VARCHAR(50),
                    seller VARCHAR(200),
                    source_url TEXT,
                    zone VARCHAR(10),
                    division VARCHAR(50),
                    currency VARCHAR(10) DEFAULT 'BDT',
                    collected_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS nppi_indices (
                    id UUID PRIMARY KEY,
                    agency VARCHAR(10) NOT NULL,
                    zone VARCHAR(10) NOT NULL,
                    category VARCHAR(100),
                    period_start DATE NOT NULL,
                    period_end DATE NOT NULL,
                    index_value DECIMAL(10,4),
                    base_value DECIMAL(10,4),
                    base_period VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            # Indexes
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_material_prices_cat ON material_prices(category)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_material_prices_collected ON material_prices(collected_at)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_nppi_agency_zone ON nppi_indices(agency, zone, period_start)"))
            await conn.commit()
        logger.info("material_prices + nppi_indices tables ready")

    # ── NPPI Computation ─────────────────────────────────────────────

    async def _compute_nppi(self) -> AgentResult:
        """Compute NPPI indices per agency per zone from 28-day material price history."""
        from app.db.database import get_session
        from sqlalchemy import text

        await self._ensure_table()
        now = datetime.now(timezone.utc)
        period_end = now.date()
        period_start = period_end - timedelta(days=NPPI_INTERVAL_DAYS)

        results = {"indices": [], "agencies_computed": 0, "zones_computed": 0}
        agencies = ["BWDB", "PWD", "LGED"]
        zones = ["A", "B", "C", "D"]

        async with get_session() as session:
            for agency in agencies:
                for zone in zones:
                    try:
                        # Get average prices for this period
                        rows = await session.execute(
                            text("""
                                SELECT category, AVG(price_bdt) as avg_price, COUNT(*) as samples
                                FROM material_prices
                                WHERE (zone = :zone OR zone = '')
                                  AND collected_at >= :start
                                  AND collected_at <= :end
                                  AND price_bdt > 0
                                GROUP BY category
                            """),
                            {"zone": zone, "start": period_start, "end": period_end}
                        )
                        period_data = {r[0]: {"avg": float(r[1]), "samples": r[2]} for r in rows.fetchall()}

                        if not period_data:
                            continue

                        # Get base period average (first 28 days of data)
                        rows_base = await session.execute(
                            text("""
                                SELECT category, AVG(price_bdt) as avg_price
                                FROM material_prices
                                WHERE (zone = :zone OR zone = '')
                                  AND category IN :cats
                                  AND price_bdt > 0
                                GROUP BY category
                                ORDER BY MIN(collected_at) ASC
                                LIMIT 100
                            """),
                            {"zone": zone, "cats": tuple(period_data.keys())}
                        )
                        base_data = {r[0]: float(r[1]) for r in rows_base.fetchall()}

                        if not base_data:
                            base_data = {cat: info["avg"] for cat, info in period_data.items()}
                            base_period = "current_period_baseline"
                        else:
                            base_period = "earliest_28d"

                        # Weighted index = sum(current/base * weight) / sum(weights)
                        total_weight = 0.0
                        weighted_index = 0.0
                        for cat, info in period_data.items():
                            base = base_data.get(cat, info["avg"])
                            if base <= 0:
                                continue
                            weight = min(info["samples"], 10)
                            weighted_index += (info["avg"] / base) * weight
                            total_weight += weight

                        if total_weight <= 0:
                            continue

                        index_value = (weighted_index / total_weight) * 100
                        base_val = 100.0

                        index_id = str(uuid.uuid4())
                        async with session.begin_nested():
                            await session.execute(
                                text("""
                                    INSERT INTO nppi_indices
                                        (id, agency, zone, category, period_start, period_end,
                                         index_value, base_value, base_period, created_at)
                                    VALUES (:id, :agency, :zone, :cat, :pstart, :pend,
                                            :ival, :bval, :bperiod, :now)
                                """),
                                {
                                    "id": index_id,
                                    "agency": agency,
                                    "zone": zone,
                                    "cat": "composite",
                                    "pstart": period_start,
                                    "pend": period_end,
                                    "ival": round(index_value, 4),
                                    "bval": round(base_val, 4),
                                    "bperiod": base_period,
                                    "now": now,
                                }
                            )
                        results["indices"].append({
                            "agency": agency, "zone": zone,
                            "index": round(index_value, 2),
                            "categories": len(period_data),
                            "samples": sum(d["samples"] for d in period_data.values()),
                        })
                        results["zones_computed"] += 1

                    except Exception as e:
                        logger.debug(f"NPPI compute failed {agency}/{zone}: {e}")

            if results["indices"]:
                await session.commit()
                results["agencies_computed"] = len(set(d["agency"] for d in results["indices"]))

        summary_counts = {d["agency"]: d["index"] for d in results["indices"]}
        await self.share_knowledge(
            entry_type="nppi_update",
            tender_id="_market",
            data=results,
            summary=f"NPPI: {results['zones_computed']} zone-agency indices computed",
            tags=["nppi", "material_prices", "index"],
        )

        return AgentResult(status=AgentStatus.SUCCESS, output={
            "indices": results["indices"],
            "agencies_computed": results["agencies_computed"],
            "zones_computed": results["zones_computed"],
            "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
        })
