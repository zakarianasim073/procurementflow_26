# EVT-01: Tender Events

## tender.discovered

Fired when TenderRadar finds new tenders.

```json
{
  "event_type": "tender.discovered",
  "data": {
    "tender_id": "1298004",
    "title": "Construction of Bridge over River X",
    "agency_code": "BWDB",
    "estimated_amount": 45000000,
    "closing_date": "2026-08-15",
    "category": "Works",
    "zone": "A",
    "source": "agent-001"
  }
}
```

## tender.acquired

Fired when TenderAcquisition completes document download.

```json
{
  "event_type": "tender.acquired",
  "data": {
    "tender_id": "1298004",
    "downloaded_files": ["notice.pdf", "section1.pdf", ...],
    "boq_items_count": 45,
    "has_tds": true,
    "source": "agent-002"
  }
}
```

## tender.prescreened

Fired when TenderPreScreener completes.

```json
{
  "event_type": "tender.prescreened",
  "data": {
    "tender_id": "1298004",
    "eligible": true,
    "score": 82,
    "gaps": [],
    "source": "agent-038"
  }
}
```

## tender.compared

Fired when BOQ comparison completes.

```json
{
  "event_type": "tender.compared",
  "data": {
    "tender_id": "1298004",
    "items_count": 45,
    "total_sor": 42000000,
    "total_quoted": 38500000,
    "avg_diff_pct": -8.3,
    "source": "boq_processor"
  }
}
```

## tender.qualified

Fired when qualification scoring completes.

```json
{
  "event_type": "tender.qualified",
  "data": {
    "tender_id": "1298004",
    "contractor_id": "canonical_123",
    "composite_score": 79,
    "recommendation": "BID",
    "source": "tender_matching"
  }
}
```

## tender.decided

Fired when bid/no-bid decision is made.

```json
{
  "event_type": "tender.decided",
  "data": {
    "tender_id": "1298004",
    "decision": "BID",
    "score": 78.5,
    "confidence": 0.82,
    "discount_range": [8, 12],
    "source": "agent-039"
  }
}
```

## tender.corrigendum

Fired when corrigendum is detected.

```json
{
  "event_type": "tender.corrigendum",
  "data": {
    "tender_id": "1298004",
    "changes": [
      { "field": "closing_date", "old": "2026-08-01", "new": "2026-08-15" },
      { "field": "estimated_amount", "old": 42000000, "new": 45000000 }
    ],
    "source": "agent-003"
  }
}
```

## tender.awarded

Fired when tender award is detected.

```json
{
  "event_type": "tender.awarded",
  "data": {
    "tender_id": "1298004",
    "contractor": "ABC Construction Ltd",
    "award_amount": 38500000,
    "discount_pct": 14.4,
    "source": "agent-014"
  }
}
```
