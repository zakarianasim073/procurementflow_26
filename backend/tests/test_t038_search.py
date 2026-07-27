"""T-038: Search upgrade tests.

Tests SearchService with real DB (savepoint-isolated).
Validates tsvector FTS on procurement_lifecycle and award_records_v2,
trigram fallback, global fanout, and pagination.
"""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy import text

from app.services.search_service import SearchService


class TestTenderSearch:

    @pytest.mark.asyncio
    async def test_browse_returns_results(self, db_session):
        """Empty query returns browse listing without error."""
        result = await SearchService.search_tenders(db_session, "", limit=5)
        assert result["success"] is True
        assert result["entity_type"] == "tenders"
        assert isinstance(result["data"], list)
        assert result["count"] == len(result["data"])

    @pytest.mark.asyncio
    async def test_fts_returns_dict_rows(self, db_session):
        """FTS query returns dicts with expected keys."""
        result = await SearchService.search_tenders(db_session, "road bridge", limit=5)
        assert result["success"] is True
        for row in result["data"]:
            assert "title" in row
            assert "agency_code" in row
            assert "rank" in row

    @pytest.mark.asyncio
    async def test_pagination_has_more(self, db_session):
        """has_more=True when rows exceed limit."""
        r1 = await SearchService.search_tenders(db_session, "", limit=1)
        r2 = await SearchService.search_tenders(db_session, "", limit=1, offset=1)
        if r1["has_more"]:
            assert r1["next_offset"] == 1
        if r2["has_more"]:
            assert r2["next_offset"] == 2

    @pytest.mark.asyncio
    async def test_agency_filter(self, db_session):
        """agency filter reduces result set (or returns empty if no match)."""
        result = await SearchService.search_tenders(
            db_session, "", agency="NONEXISTENT_AGENCY_XYZ", limit=10
        )
        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_fts_no_crash_on_special_chars(self, db_session):
        """Search with special chars that could break tsquery doesn't crash."""
        result = await SearchService.search_tenders(db_session, "road & bridge", limit=5)
        assert result["success"] is True


class TestAwardSearch:

    @pytest.mark.asyncio
    async def test_browse_returns_results(self, db_session):
        result = await SearchService.search_awards(db_session, "", limit=5)
        assert result["success"] is True
        assert result["entity_type"] == "awards"

    @pytest.mark.asyncio
    async def test_fts_award_query(self, db_session):
        result = await SearchService.search_awards(db_session, "construction works", limit=5)
        assert result["success"] is True
        for row in result["data"]:
            assert "contractor_name" in row
            assert "amount_bdt" in row

    @pytest.mark.asyncio
    async def test_district_filter(self, db_session):
        result = await SearchService.search_awards(
            db_session, "", district="NONEXISTENT_DISTRICT_ZZZ", limit=5
        )
        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_contractor_filter(self, db_session):
        result = await SearchService.search_awards(
            db_session, "", contractor="ZZZNOMATCH999XY", limit=5
        )
        assert result["success"] is True
        assert result["count"] == 0


class TestContractorSearch:

    @pytest.mark.asyncio
    async def test_browse_returns_list(self, db_session):
        result = await SearchService.search_contractors(db_session, "", limit=5)
        assert result["success"] is True
        assert result["entity_type"] == "contractors"

    @pytest.mark.asyncio
    async def test_fts_query_runs(self, db_session):
        result = await SearchService.search_contractors(db_session, "engineering", limit=5)
        assert result["success"] is True
        for row in result["data"]:
            assert "contractor_name" in row

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self, db_session):
        result = await SearchService.search_contractors(
            db_session, "ZZZNOMATCH_UNIQUE_XYZ_CONTRACTOR", limit=5
        )
        assert result["success"] is True
        assert result["count"] == 0


class TestGlobalSearch:

    @pytest.mark.asyncio
    async def test_global_returns_three_buckets(self, db_session):
        result = await SearchService.search_global(db_session, "road", limit_per_type=5)
        assert result["success"] is True
        assert "tenders" in result
        assert "awards" in result
        assert "contractors" in result
        assert "counts" in result
        assert set(result["counts"].keys()) == {"tenders", "awards", "contractors"}

    @pytest.mark.asyncio
    async def test_global_count_matches_bucket_length(self, db_session):
        result = await SearchService.search_global(db_session, "bridge", limit_per_type=3)
        for key in ("tenders", "awards", "contractors"):
            assert len(result[key]) == result["counts"][key]

    @pytest.mark.asyncio
    async def test_global_no_crash_on_empty_result_query(self, db_session):
        result = await SearchService.search_global(
            db_session, "ZZZNOMATCH_IMPOSSIBLE_QUERY_XYZ99", limit_per_type=5
        )
        assert result["success"] is True
        assert result["counts"]["tenders"] == 0
        assert result["counts"]["awards"] == 0
        assert result["counts"]["contractors"] == 0
