"""ProcureFlow event consumption (X-003). Wire format = Enterprise_OS/contracts/EVENT_CONTRACTS.md;
EPDP publishes, we consume via Redis Streams — never via imports (L2)."""

from app.events.subscriber import EventSubscriber, IncomingEvent

__all__ = ["EventSubscriber", "IncomingEvent"]
