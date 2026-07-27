"""
Agent 28 — Syndicate & Collusion Radar (PPR 2025 Regime-Aware)
Detects tender syndicates, dummy bidders, and bid-rigging cartels using historical award data.
PPR 2025 SLT/ALT thresholds used to calibrate abnormal discount detection — discounts near ALT
are flagged differently than PPR 2008 ±10% cap violations.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import Counter

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agents.core.regime import get_regime, get_thresholds, get_slt_status, get_regime_label, REGIME_PPR2025, REGIME_PPR2008

logger = logging.getLogger(__name__)


class SyndicateRadarAgent(BaseAgent):
    agent_id = "agent-028-syndicate-radar"
    agent_name = "Syndicate & Collusion Radar (Regime-Aware)"
    description = "Detects bid-rigging, dummy bidders, rotating winners, cover pricing with PPR 2008 / PPR 2025 regime-aware discount calibration."
    dependencies: List[str] = ["agent-014-award-intelligence"]
    version = "2.0.0"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        awards = context.get("awards", context.get("upstream", {}).get("agent-014-award-intelligence", {}).get("awards", []))
        tenders = context.get("tenders", [])

        regime = context.get("regime") or get_regime(
            context.get("tender_info", {}).get("opening_date") or
            context.get("tender_info", {}).get("submission_date")
        )

        analysis = self._analyze_all(awards, tenders, regime)

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output=analysis,
        )

    def _analyze_all(self, awards: List[Dict], tenders: List[Dict], regime: str = REGIME_PPR2008) -> Dict[str, Any]:
        """Run all syndicate detection algorithms with regime-aware discount calibration."""
        thresholds = get_thresholds(regime)
        return {
            "rotating_winners": self._detect_rotating_winners(awards),
            "cover_pricing": self._detect_cover_pricing(awards),
            "market_allocation": self._detect_market_allocation(awards),
            "abnormal_discounts": self._detect_abnormal_discounts(awards, regime, thresholds),
            "bidder_clustering": self._detect_bidder_clustering(awards, tenders),
            "flags": self._generate_flags(awards, regime),
            "summary": self._generate_summary(awards, regime),
            "regime": regime,
            "regime_label": get_regime_label(regime),
        }

    def _detect_rotating_winners(self, awards: List[Dict]) -> List[Dict]:
        """
        Detect rotating winner patterns:
        In a cartel, companies take turns winning projects at similar values.
        """
        from collections import defaultdict
        
        # Group by procuring entity
        entity_groups = defaultdict(list)
        for a in awards:
            entity_groups[a.get("procuring_entity", "Unknown")].append(a)
        
        findings = []
        for entity, entity_awards in entity_groups.items():
            if len(entity_awards) < 4:
                continue
            
            # Check if winners rotate in a predictable pattern
            winners = [a.get("contractor_name", "") for a in sorted(entity_awards, key=lambda x: x.get("award_date", ""))]
            winner_counts = Counter(winners)
            
            # If 3+ bidders have won at least once in recent tenders from same entity
            active_winners = [w for w, c in winner_counts.items() if c >= 1]
            if len(active_winners) >= 3:
                # Check for rotation: do wins alternate?
                rotation_pattern = []
                for i in range(len(winners) - 2):
                    if winners[i] != winners[i+1] and winners[i+1] != winners[i+2]:
                        rotation_pattern.append(True)
                    else:
                        rotation_pattern.append(False)
                
                rotation_ratio = sum(rotation_pattern) / max(len(rotation_pattern), 1)
                
                if rotation_ratio > 0.6 and len(active_winners) >= 3:
                    findings.append({
                        "entity": entity,
                        "pattern": "rotating_winners",
                        "confidence": min(rotation_ratio * 1.2, 0.95),
                        "bidders": active_winners,
                        "recent_wins": winners[-6:],
                        "analysis": f"Winners rotate {rotation_ratio:.0%} of time — possible bid-rigging cartel",
                    })
        
        return findings

    def _detect_cover_pricing(self, awards: List[Dict]) -> List[Dict]:
        """
        Detect cover pricing: when a bidder submits a deliberately high price
        to make another bidder win, or bids exactly the same rate pattern.
        """
        from collections import defaultdict
        
        findings = []
        
        # Group awards by tender
        tender_groups = defaultdict(list)
        for a in awards:
            tender_groups[a.get("tender_id", "Unknown")].append(a)
        
        for tender_id, participants in tender_groups.items():
            if len(participants) < 3:
                continue
            
            amounts = []
            for p in participants:
                try:
                    amounts.append(float(p.get("awarded_amount", 0) or p.get("bid_amount", 0)))
                except (ValueError, TypeError):
                    continue
            
            if len(amounts) < 3:
                continue
            
            sorted_amounts = sorted(amounts)
            lowest = sorted_amounts[0] if sorted_amounts else 0
            second_lowest = sorted_amounts[1] if len(sorted_amounts) >= 2 else 0
            highest = sorted_amounts[-1] if sorted_amounts else 0
            
            if highest > 0 and lowest > 0:
                # Cover pricing: lowest and second-lowest bids are tightly clustered.
                if len(sorted_amounts) >= 3 and second_lowest > 0:
                    gap = (second_lowest - lowest) / lowest
                    if gap < 0.02:  # < 2% gap between lowest and second-lowest = cover price
                        findings.append({
                            "tender_id": tender_id,
                            "pattern": "cover_pricing",
                            "confidence": min(0.5 + (1 - gap / 0.02) * 0.4, 0.9),
                            "lowest_bid": lowest,
                            "second_lowest": second_lowest,
                            "highest_bid": highest,
                            "analysis": f"Lowest bids tightly clustered (gap: {gap:.1%}) — possible cover pricing",
                        })
        
        return findings

    def _detect_market_allocation(self, awards: List[Dict]) -> List[Dict]:
        """
        Detect if bidders have carved up districts/agencies among themselves.
        "You stay in Gazipur, I'll take Narayanganj."
        """
        from collections import defaultdict
        
        findings = []
        
        # Group winners by district
        district_winners = defaultdict(set)
        winner_districts = defaultdict(set)
        
        for a in awards:
            district = a.get("district", "") or a.get("location", "")
            winner = a.get("contractor_name", "")
            if district and winner:
                district_winners[district].add(winner)
                winner_districts[winner].add(district)
        
        # If a bidder ONLY operates in exclusive districts
        for winner, districts in winner_districts.items():
            exclusive_territories = []
            for d in districts:
                competitors_in_district = district_winners.get(d, set())
                # Remove self
                competitors_in_district = competitors_in_district - {winner}
                if len(competitors_in_district) <= 1:  # 0 or 1 competitor = exclusive
                    exclusive_territories.append(d)
            
            if len(exclusive_territories) >= 2 and len(districts) >= 3:
                findings.append({
                    "contractor": winner,
                    "pattern": "market_allocation",
                    "confidence": min(len(exclusive_territories) / max(len(districts), 1) * 0.8, 0.85),
                    "exclusive_districts": exclusive_territories,
                    "all_districts": list(districts),
                    "analysis": f"Operates in {len(exclusive_territories)}/{len(districts)} exclusive districts — possible territory allocation",
                })
        
        return findings

    def _detect_abnormal_discounts(self, awards: List[Dict], regime: str = REGIME_PPR2008,
                                    thresholds: Optional[Dict] = None) -> List[Dict]:
        """
        Flag consistent abnormal discount patterns, regime-aware.
        PPR 2008: discounts consistently near ±10% cap are suspicious.
        PPR 2025: discounts near SLT (70%) or ALT (60%) thresholds trigger higher severity.
        """
        findings = []
        discounts = []

        if thresholds is None:
            thresholds = get_thresholds(regime)

        slt_discount_pct = round((1 - thresholds["slt_threshold"]) * 100, 1)  # 30%
        alt_discount_pct = round((1 - thresholds["alt_threshold"]) * 100, 1)  # 40%

        for a in awards:
            try:
                est = float(a.get("estimated_cost", 0))
                awarded = float(a.get("awarded_amount", 0))
                if est > 0 and awarded > 0:
                    discount = (1 - awarded / est) * 100
                    discounts.append({
                        "tender": a.get("tender_id", ""),
                        "contractor": a.get("contractor_name", ""),
                        "discount_pct": round(discount, 2),
                        "estimated": est,
                        "awarded": awarded,
                    })
            except (ValueError, TypeError):
                continue

        from collections import defaultdict
        contractor_discounts = defaultdict(list)
        for d in discounts:
            contractor_discounts[d["contractor"]].append(d["discount_pct"])

        for contractor, dlist in contractor_discounts.items():
            if len(dlist) >= 3:
                avg_d = statistics.mean(dlist)
                stdev_d = statistics.stdev(dlist) if len(dlist) > 1 else 0

                if stdev_d < 1.0 and 3 <= avg_d <= 8:
                    severity = "medium"
                    analysis = f"Consistently bids {avg_d:.1f}±{stdev_d:.1f}% discount — possible pre-arranged pricing"

                    if regime == REGIME_PPR2025:
                        if avg_d >= alt_discount_pct * 0.85:
                            severity = "high"
                            analysis += f" | Near ALT threshold ({alt_discount_pct}%) — bid-rigging risk elevated under PPR 2025"
                        elif avg_d >= slt_discount_pct * 0.85:
                            severity = "high"
                            analysis += f" | Near SLT threshold ({slt_discount_pct}%) — may indicate coordinated SLT-level bids"
                    else:
                        cap_pct = round(thresholds["cap_threshold"] * 100, 1) if thresholds.get("cap_threshold") else 10.0
                        if avg_d >= cap_pct * 0.8:
                            severity = "high"
                            analysis += f" | Near ±{cap_pct}% cap — possible cap-level collusion"

                    findings.append({
                        "contractor": contractor,
                        "pattern": "abnormal_discount_consistency",
                        "severity": severity,
                        "confidence": min(0.5 + (1 - stdev_d) * 0.3, 0.9),
                        "avg_discount_pct": round(avg_d, 2),
                        "stdev_discount": round(stdev_d, 2),
                        "num_awards": len(dlist),
                        "regime": regime,
                        "analysis": analysis,
                    })

        return findings

    def _detect_bidder_clustering(self, awards: List[Dict], tenders: List[Dict]) -> List[Dict]:
        """Detect if same group of bidders always appears together (clique detection)."""
        from collections import defaultdict
        
        findings = []
        tender_bidders = defaultdict(set)
        
        for a in awards:
            tender_bidders[a.get("tender_id", "")].add(a.get("contractor_name", ""))
        
        # Count co-occurrences
        cooccurrence = defaultdict(lambda: defaultdict(int))
        for bidders in tender_bidders.values():
            bidder_list = list(bidders)
            for i in range(len(bidder_list)):
                for j in range(i+1, len(bidder_list)):
                    cooccurrence[bidder_list[i]][bidder_list[j]] += 1
                    cooccurrence[bidder_list[j]][bidder_list[i]] += 1
        
        # Find cliques (groups that always appear together)
        for bidder, associates in cooccurrence.items():
            total = sum(1 for b in tender_bidders.values() if bidder in b)
            if total >= 3:
                frequent = [(assoc, count) for assoc, count in associates.items() 
                           if count / total > 0.7]
                if len(frequent) >= 2:
                    findings.append({
                        "contractor": bidder,
                        "pattern": "bidder_clustering",
                        "confidence": min(0.5 + len(frequent) * 0.1, 0.9),
                        "frequent_associates": [{"name": assoc, "cooccurrence_pct": round(count/total, 2)} 
                                               for assoc, count in frequent],
                        "analysis": f"Consistently bids with {len(frequent)} same contractors — possible bidding ring",
                    })
        
        return findings

    def _generate_flags(self, awards: List[Dict], regime: str = REGIME_PPR2008) -> List[Dict]:
        """Generate high-level red flags for each tender, regime-aware."""
        from collections import defaultdict
        flags = []

        tender_counts = defaultdict(int)
        for a in awards:
            tender_counts[a.get("tender_id", "")] += 1

        for tender_id, count in tender_counts.items():
            if count <= 2:
                flags.append({
                    "tender_id": tender_id,
                    "flag": "insufficient_competition",
                    "severity": "high",
                    "message": f"Only {count} bidder(s) — possible single-bidder scenario",
                    "regime": regime,
                })
            elif count == 3:
                msg = f"Only {count} bidders — minimum competition threshold"
                if regime == REGIME_PPR2025:
                    msg += " | PPR 2025 encourages wider competition; low bidder counts raise SLT/ALT risk"
                flags.append({
                    "tender_id": tender_id,
                    "flag": "minimal_competition",
                    "severity": "medium",
                    "message": msg,
                    "regime": regime,
                })

        return flags

    def _generate_summary(self, awards: List[Dict], regime: str = REGIME_PPR2008) -> Dict[str, Any]:
        """Generate overall syndicate risk summary, regime-aware."""
        thresholds = get_thresholds(regime)
        return {
            "total_awards_analyzed": len(awards),
            "risk_level": "analyze",
            "regime": regime,
            "regime_label": get_regime_label(regime),
            "note": "Syndicate detection requires at least 20+ award records for statistically significant patterns",
            "regime_context": f"Abnormal discounts evaluated against {'PPR 2025 SLT/ALT thresholds' if regime == REGIME_PPR2025 else 'PPR 2008 ±10% cap'}",
        }
