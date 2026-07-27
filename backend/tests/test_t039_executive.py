"""T-039: Executive dashboard 2.0 — pipeline, agency spend, contractor heatmap.

Calls the endpoint functions directly with a real (savepoint-isolated) session.
"""
from __future__ import annotations

import pytest

from app.api.v1.executive import (
    get_executive_pipeline,
    get_agency_spend,
    get_contractor_heatmap,
)


class TestPipeline:

    @pytest.mark.asyncio
    async def test_pipeline_shape(self, db_session):
        result = await get_executive_pipeline(db=db_session, user=None)
        assert result["success"] is True
        assert "total_live_tenders" in result
        assert "estimated_total_pipeline_value_bdt" in result
        assert isinstance(result["agencies"], list)

    @pytest.mark.asyncio
    async def test_pipeline_agency_fields(self, db_session):
        result = await get_executive_pipeline(db=db_session, user=None)
        for a in result["agencies"]:
            assert a["live_tenders"] >= a["closing_7d"] >= 0
            assert a["closing_30d"] >= a["closing_14d"] >= a["closing_7d"]
            assert a["estimated_pipeline_value_bdt"] >= 0

    @pytest.mark.asyncio
    async def test_pipeline_totals_consistent(self, db_session):
        result = await get_executive_pipeline(db=db_session, user=None)
        assert result["total_live_tenders"] == sum(a["live_tenders"] for a in result["agencies"])


class TestAgencySpend:

    @pytest.mark.asyncio
    async def test_spend_shape(self, db_session):
        result = await get_agency_spend(years=5, db=db_session, user=None)
        assert result["success"] is True
        assert isinstance(result["years"], list)
        assert isinstance(result["agencies"], list)

    @pytest.mark.asyncio
    async def test_spend_sorted_desc(self, db_session):
        result = await get_agency_spend(years=5, db=db_session, user=None)
        spends = [a["total_spend_bdt"] for a in result["agencies"]]
        assert spends == sorted(spends, reverse=True)

    @pytest.mark.asyncio
    async def test_spend_years_are_valid(self, db_session):
        result = await get_agency_spend(years=3, db=db_session, user=None)
        assert len(result["years"]) <= 3
        for y in result["years"]:
            assert y.isdigit() and 2000 <= int(y) <= 2100

    @pytest.mark.asyncio
    async def test_spend_year_totals_match(self, db_session):
        result = await get_agency_spend(years=5, db=db_session, user=None)
        for a in result["agencies"][:5]:
            year_sum = sum(v["spend_bdt"] for v in a["years"].values())
            # per-year values are rounded to whole BDT, so allow rounding drift
            assert abs(year_sum - a["total_spend_bdt"]) < 10.0


class TestContractorHeatmap:

    @pytest.mark.asyncio
    async def test_heatmap_shape(self, db_session):
        result = await get_contractor_heatmap(top_n=10, db=db_session, user=None)
        assert result["success"] is True
        assert len(result["contractors"]) <= 10

    @pytest.mark.asyncio
    async def test_heatmap_cells_reference_valid_axes(self, db_session):
        result = await get_contractor_heatmap(top_n=10, db=db_session, user=None)
        names = {c["name"] for c in result["contractors"]}
        agencies = set(result["agencies"])
        for cell in result["cells"]:
            assert cell["contractor"] in names
            assert cell["agency_code"] in agencies
            assert cell["wins"] > 0

    @pytest.mark.asyncio
    async def test_heatmap_top_n_clamped(self, db_session):
        result = await get_contractor_heatmap(top_n=1000, db=db_session, user=None)
        assert len(result["contractors"]) <= 50

    @pytest.mark.asyncio
    async def test_heatmap_contractors_sorted_by_value(self, db_session):
        result = await get_contractor_heatmap(top_n=10, db=db_session, user=None)
        values = [c["total_value_bdt"] for c in result["contractors"]]
        assert values == sorted(values, reverse=True)
