from unittest.mock import AsyncMock, Mock

import pytest

from app.services.tender_matching_service import TenderMatchingService
from app.services.intelligence.domain.services.discovery_service import DiscoveryService


@pytest.mark.asyncio
async def test_lifecycle_rebuild_links_normalized_works_packages():
    db = AsyncMock()
    db.scalar.return_value = True
    insert_result = Mock(rowcount=1)
    stats_result = Mock()
    stats_result.mappings.return_value.one.return_value = {
        "rows_inserted": 1,
        "matched": 1,
        "app_only": 0,
        "ec_only": 0,
        "tender_only": 0,
    }
    db.execute.side_effect = [Mock(), insert_result, stats_result]

    await TenderMatchingService(db).rebuild_procurement_lifecycle()

    sql = str(db.execute.await_args_list[1].args[0])
    assert "app.normalized_package_no = vt.normalized_package_no" in sql
    assert "aw.normalized_package_no = vt.normalized_package_no" in sql
    assert "lower(category) = 'works'" in sql
    assert "JOIN app_latest app" in sql


def test_app_title_leading_package_code_is_recovered_conservatively():
    service = DiscoveryService(AsyncMock())
    assert (
        service._extract_package_from_title(
            "PWD/SYL/2025-2026/SDE1/T-82 | Cleaning and repair works"
        )
        == "PWD/SYL/2025-2026/SDE1/T-82"
    )
    assert service._extract_package_from_title("Construction of a rural road") is None
