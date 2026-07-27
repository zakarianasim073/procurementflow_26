# EVT-03: Knowledge Events

## knowledge.stored

Fired when knowledge entry is stored.

```json
{
  "event_type": "knowledge.stored",
  "data": {
    "entry_id": 123,
    "entry_type": "boq_text",
    "tender_id": "1298004",
    "agent_id": "agent-002",
    "size_bytes": 45000
  }
}
```

## knowledge.queried

Fired when knowledge is queried (for analytics).

```json
{
  "event_type": "knowledge.queried",
  "data": {
    "query_type": "by_type+tender",
    "entry_type": "boq_text",
    "tender_id": "1298004",
    "cache_hit": true,
    "result_count": 1
  }
}
```

## knowledge.synced

Fired when knowledge cache is warmed from DB.

```json
{
  "event_type": "knowledge.synced",
  "data": {
    "entries_loaded": 10000,
    "cache_size_bytes": 50000000,
    "duration_ms": 2500
  }
}
```

## knowledge.graph_updated

Fired when knowledge graph edges are added/modified.

```json
{
  "event_type": "knowledge.graph_updated",
  "data": {
    "nodes_added": 3,
    "edges_added": 5,
    "source_entity": "tender:1298004",
    "target_entities": ["contractor:ABC", "agency:BWDB"]
  }
}
```
