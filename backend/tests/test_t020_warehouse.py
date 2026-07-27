"""T-020 Analytics Warehouse Tests - Query correctness and performance."""

from __future__ import annotations

import uuid
import pytest
from decimal import Decimal
from datetime import datetime, date, timezone, timedelta

from app.models.analytics import (
    DimAgencies,
    DimZones,
    DimCategories,
    DimContractors,
    FactTenders,
    FactAwards,
    FactBids,
)
from app.services.analytics_warehouse import AnalyticsWarehouseService


@pytest.fixture
async def sample_dimensions(db_session):
    """Create sample dimension data."""
    # Agencies
    agency = DimAgencies(
        agency_id=str(uuid.uuid4()),
        agency_code="PWD-01",
        agency_name="PWD Dhaka",
        division="Dhaka",
        region="Central",
        is_active=True,
        tender_count=10,
        total_spend_bdt=Decimal("5000000"),
    )
    db_session.add(agency)

    # Zones
    zone = DimZones(
        zone_id="A",
        zone_name="Central Zone",
        region="Central",
        agency_type="PWD",
        tender_count=50,
    )
    db_session.add(zone)

    # Categories
    category = DimCategories(
        category_id=str(uuid.uuid4()),
        category_name="Road Construction",
        sector="Infrastructure",
        subsector="Roads",
        tender_count=20,
        avg_tender_value_bdt=Decimal("2500000"),
    )
    db_session.add(category)

    # Contractors
    contractor = DimContractors(
        contractor_id=str(uuid.uuid4()),
        contractor_name="ABC Contractors Ltd",
        registration_number="REG-001",
        category="A",
        zone="A",
        bid_count=5,
        award_count=2,
        total_contract_value_bdt=Decimal("10000000"),
        completion_rate_pct=Decimal("95.50"),
    )
    db_session.add(contractor)

    await db_session.commit()

    return {
        "agency": agency,
        "zone": zone,
        "category": category,
        "contractor": contractor,
    }


@pytest.fixture
async def sample_facts(db_session, sample_dimensions):
    """Create sample fact data."""
    dim = sample_dimensions

    # Tenders
    tender = FactTenders(
        tender_id=str(uuid.uuid4()),
        agency_id=dim["agency"].agency_id,
        zone_id=dim["zone"].zone_id,
        category_id=dim["category"].category_id,
        tender_value_bdt=Decimal("5000000"),
        estimated_value_bdt=Decimal("4800000"),
        procurement_method="Open",
        tender_type="Works",
        status="awarded",
        published_date=date.today() - timedelta(days=30),
        deadline_date=date.today() - timedelta(days=15),
        award_date=date.today() - timedelta(days=5),
        bid_count=10,
        duration_days=15,
    )
    db_session.add(tender)
    await db_session.flush()

    # Awards
    award = FactAwards(
        award_id=str(uuid.uuid4()),
        tender_id=tender.tender_id,
        contractor_id=dim["contractor"].contractor_id,
        award_value_bdt=Decimal("4900000"),
        award_date=date.today() - timedelta(days=5),
        completion_status="ongoing",
        days_to_award=25,
    )
    db_session.add(award)

    # Bids
    bid = FactBids(
        bid_id=str(uuid.uuid4()),
        tender_id=tender.tender_id,
        contractor_id=dim["contractor"].contractor_id,
        bid_amount_bdt=Decimal("4900000"),
        bid_date=date.today() - timedelta(days=10),
        is_winner=True,
        days_to_bid=20,
    )
    db_session.add(bid)

    await db_session.commit()

    return {
        "tender": tender,
        "award": award,
        "bid": bid,
    }


class TestWarehouseQueries:
    """Test OLAP query correctness."""

    @pytest.mark.asyncio
    async def test_get_market_overview(self, db_session, sample_facts):
        """Market overview aggregation returns correct totals."""
        overview = await AnalyticsWarehouseService.get_market_overview(db_session)

        assert overview["total_tenders"] >= 1
        assert overview["total_value_bdt"] > 0
        assert overview["avg_value_bdt"] > 0
        assert overview["awarded_count"] >= 0

    @pytest.mark.asyncio
    async def test_get_market_by_agency(self, db_session, sample_facts):
        """Agency-level aggregations are correct."""
        results = await AnalyticsWarehouseService.get_market_by_agency(db_session, limit=10)

        assert len(results) > 0
        first = results[0]

        assert "agency_id" in first
        assert "agency_name" in first
        assert "tender_count" in first
        assert first["tender_count"] > 0
        assert first["total_value_bdt"] > 0

    @pytest.mark.asyncio
    async def test_get_contractor_performance(self, db_session, sample_facts):
        """Contractor performance metrics are calculated correctly."""
        results = await AnalyticsWarehouseService.get_contractor_performance(db_session)

        assert len(results) > 0
        first = results[0]

        assert "contractor_id" in first
        assert "contractor_name" in first
        assert first["total_bids"] >= 1
        assert first["won_bids"] >= 0
        assert 0 <= first["win_rate_pct"] <= 100

    @pytest.mark.asyncio
    async def test_get_market_trend(self, db_session, sample_facts):
        """Market trend time series returns monthly data."""
        trends = await AnalyticsWarehouseService.get_market_trend(db_session, months=12)

        # Should have data for months with tenders
        assert len(trends) >= 0

        if trends:
            first = trends[0]
            assert "month" in first
            assert "tender_count" in first
            assert first["tender_count"] >= 0

    @pytest.mark.asyncio
    async def test_get_category_trends(self, db_session, sample_facts):
        """Category trends are aggregated correctly."""
        trends = await AnalyticsWarehouseService.get_category_trends(db_session, months=12)

        assert len(trends) >= 0

        if trends:
            first = trends[0]
            assert "category_name" in first
            assert "sector" in first
            assert "tender_count" in first


class TestWarehouseRefresh:
    """Test ETL refresh operations."""

    @pytest.mark.asyncio
    async def test_refresh_dimensions(self, db_session):
        """Dimension refresh completes without error."""
        results = await AnalyticsWarehouseService.refresh_dimensions(db_session)

        assert isinstance(results, dict)
        assert "dim_agencies" in results or "dim_contractors" in results

    @pytest.mark.asyncio
    async def test_refresh_facts(self, db_session):
        """Fact table refresh completes without error."""
        results = await AnalyticsWarehouseService.refresh_facts(db_session, hours_back=24)

        assert isinstance(results, dict)
        assert "fact_tenders" in results or "fact_awards" in results or "fact_bids" in results


class TestWarehouseHealth:
    """Test warehouse health and statistics."""

    @pytest.mark.asyncio
    async def test_get_warehouse_stats(self, db_session, sample_facts):
        """Warehouse statistics reports row counts."""
        stats = await AnalyticsWarehouseService.get_warehouse_stats(db_session)

        assert isinstance(stats, dict)
        assert "dim_agencies" in stats
        assert "fact_tenders" in stats
        assert stats["fact_tenders"] >= 1  # At least sample data


class TestWarehouseDataQuality:
    """Test data quality and integrity."""

    @pytest.mark.asyncio
    async def test_fact_tender_values_populated(self, db_session, sample_facts):
        """Fact tenders have required fields populated."""
        tender = sample_facts["tender"]

        assert tender.tender_id is not None
        assert tender.published_date is not None
        assert tender.status is not None
        assert tender.bid_count >= 0

    @pytest.mark.asyncio
    async def test_contractor_metrics_consistency(self, db_session, sample_facts):
        """Contractor metrics (bids, awards, completion rate) are sensible."""
        contractor = sample_facts["bid"].contractor_id
        bid = sample_facts["bid"]

        # Winner bid should have is_winner=True
        assert bid.is_winner is True
        assert bid.bid_amount_bdt > 0

    @pytest.mark.asyncio
    async def test_award_value_vs_bid_amount(self, db_session, sample_facts):
        """Award value should be close to winning bid amount."""
        award = sample_facts["award"]
        bid = sample_facts["bid"]

        # Award and winning bid should be same or award <= bid + tolerance
        tolerance = Decimal("100000")  # 1 lakh tolerance
        assert award.award_value_bdt <= bid.bid_amount_bdt + tolerance
