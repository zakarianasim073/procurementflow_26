from app.celery_app import celery_app
from app.workers.tasks.idle_intelligence_tasks import (
    DOCUMENT_EVIDENCE,
    IDLE_AGENT_TIMEOUT_SECONDS,
    IDLE_ANALYTICAL_AGENTS,
)


def test_idle_intelligence_is_bounded_to_low_priority_queue():
    entry = celery_app.conf.beat_schedule["idle-shortlist-intelligence"]

    assert entry["task"] == "idle_shortlist_intelligence"
    assert entry["kwargs"]["limit"] == 5
    assert entry["options"]["queue"] == "low"
    assert celery_app.conf.task_routes["idle_shortlist_intelligence"]["queue"] == "low"


def test_idle_agents_are_analysis_only():
    forbidden = {
        "agent-001-tender-radar",
        "agent-002-tender-acquisition",
        "agent-003-corrigendum-watchdog",
        "agent-020-egp-rate-fill",
        "agent-024-submission-validation",
        "agent-031-whatsapp-automation",
        "agent-032-document-preparation",
        "agent-034-tender-document",
        "agent-045-opening-report",
        "agent-048-material-price-crawler",
    }

    assert forbidden.isdisjoint(IDLE_ANALYTICAL_AGENTS)
    assert "agent-005-boq-intelligence" in IDLE_ANALYTICAL_AGENTS
    assert "agent-012-market-rate-intelligence" in IDLE_ANALYTICAL_AGENTS
    assert "agent-010-ppr-compliance" in IDLE_ANALYTICAL_AGENTS
    assert DOCUMENT_EVIDENCE["agent-005-boq-intelligence"] == {"boq_text"}
    assert IDLE_AGENT_TIMEOUT_SECONDS < 60
