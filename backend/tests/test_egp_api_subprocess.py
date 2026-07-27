import asyncio
import json

import pytest

from app.api.v1.agents import _run_egp_subprocess


@pytest.mark.asyncio
async def test_egp_api_uses_subprocess(monkeypatch):
    class FakeProcess:
        returncode = 0

        async def communicate(self, payload):
            request = json.loads(payload)
            assert request["action"] == "login"
            return b'{"success": true, "session_active": true}', b""

    async def fake_create_subprocess_exec(*args, **kwargs):
        assert kwargs["stdin"] == asyncio.subprocess.PIPE
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    result = await _run_egp_subprocess({"action": "login"})

    assert result == {"success": True, "session_active": True}
