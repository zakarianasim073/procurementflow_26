from __future__ import annotations

from app.api.v1.boq import _build_boq_item_row


def test_boq_item_persistence_maps_processor_fields():
    item = _build_boq_item_row(
        "tender-db-id",
        {
            "item_no": "1",
            "code": "40-200-00",
            "desc": "Earthwork in embankment",
            "unit": "cum",
            "qty": "12.5",
            "rate": "100",
            "sor_rate": "95",
            "sor_source": "40-200-00",
            "diff": "5",
            "pct_diff": "5.26",
            "flag": "VARIANCE",
            "work_type": "Earthwork",
            "section": "Civil",
            "agency": "BWDB",
            "match_type": "code",
            "match_confidence": 1.0,
            "remarks": "EXACT CODE",
            "sor_desc": "SOR earthwork",
        },
    )

    assert item.tender_id == "tender-db-id"
    assert item.description == "Earthwork in embankment"
    assert item.quantity == 12.5
    assert item.quoted_rate == 100.0
    assert item.sor_rate == 95.0
    assert item.sor_code == "40-200-00"
    assert item.section == "Civil"
    assert item.attributes["match_type"] == "code"
