from decimal import Decimal

import pytest

from app.agents.core.base import AgentResult, AgentStatus, BaseAgent


class _Agent(BaseAgent):
    async def execute(self, context):
        return AgentResult(status=AgentStatus.SUCCESS)


@pytest.mark.asyncio
async def test_store_result_serializes_decimal_output():
    class _Session:
        def __init__(self):
            self.record = None

        def add(self, record):
            self.record = record

        async def flush(self):
            return None

    session = _Session()
    result = AgentResult(
        agent_id="agent-test",
        status=AgentStatus.SUCCESS,
        output={"amount": Decimal("12.50")},
    )

    await _Agent().store_result(result, session=session)

    assert session.record.output == {"amount": "12.50"}
