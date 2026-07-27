# EVT-02: Agent Events

## agent.started

Fired when any agent begins execution.

```json
{
  "event_type": "agent.started",
  "data": {
    "agent_id": "agent-001",
    "agent_name": "TenderRadarAgent",
    "input": { "action": "scan_live_tenders" },
    "run_id": "uuid"
  }
}
```

## agent.completed

Fired when agent completes successfully.

```json
{
  "event_type": "agent.completed",
  "data": {
    "agent_id": "agent-001",
    "agent_name": "TenderRadarAgent",
    "run_id": "uuid",
    "duration_ms": 15200,
    "output_summary": { "live_found": 12, "new_inserted": 5 }
  }
}
```

## agent.failed

Fired when agent execution fails.

```json
{
  "event_type": "agent.failed",
  "data": {
    "agent_id": "agent-002",
    "agent_name": "TenderAcquisitionAgent",
    "run_id": "uuid",
    "error": "e-GP session expired after 3 retries",
    "duration_ms": 45000,
    "retry_count": 3
  }
}
```

## agent.thought_created

Fired when agent creates a thought for human review.

```json
{
  "event_type": "agent.thought_created",
  "data": {
    "agent_id": "agent-016",
    "tender_id": "1298004",
    "thought_type": "win_probability",
    "thought_id": "uuid",
    "data": { "probability": 0.68, "confidence": 0.75 }
  }
}
```

## agent.thought_resolved

Fired when human approves/rejects a thought.

```json
{
  "event_type": "agent.thought_resolved",
  "data": {
    "thought_id": "uuid",
    "resolution": "approved",
    "resolved_by": "user_uuid",
    "comment": "Looks reasonable"
  }
}
```

## pipeline.completed

Fired when multi-agent pipeline completes.

```json
{
  "event_type": "pipeline.completed",
  "data": {
    "pipeline_id": "uuid",
    "mode": "intelligence",
    "phases_completed": 6,
    "agents_executed": 10,
    "duration_ms": 180000,
    "status": "completed",
    "summary": { "tenders_found": 5, "decisions": ["BID", "NO-BID", "BID"] }
  }
}
```
