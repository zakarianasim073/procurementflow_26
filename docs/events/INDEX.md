# Event Contracts — Phase H

> Async event schemas for inter-agent communication and webhook delivery.

## Event Categories

| Category | File | Events |
|----------|------|--------|
| Tender Events | [EVT-01_Tender.md](EVT-01_Tender.md) | 8 events |
| Agent Events | [EVT-02_Agent.md](EVT-02_Agent.md) | 6 events |
| Knowledge Events | [EVT-03_Knowledge.md](EVT-03_Knowledge.md) | 4 events |
| Enterprise Events | [EVT-04_Enterprise.md](EVT-04_Enterprise.md) | 5 events |

## Base Event Schema

```json
{
  "event_id": "uuid",
  "event_type": "string",
  "timestamp": "2026-07-24T02:00:00Z",
  "source": "string",
  "data": {},
  "metadata": {
    "tenant_id": "string",
    "user_id": "string",
    "correlation_id": "string"
  }
}
```

## Event Delivery

| Channel | Mechanism | Guarantees |
|---------|-----------|-----------|
| In-process | Brain.broadcast() | At-most-once |
| PostgreSQL | knowledge_entries | At-least-once |
| Webhook | WebhookService | At-least-once with retry |
