from __future__ import annotations

from app.agents.egp_client import eGPClient
from app.core.config import settings
from app.core.security import create_refresh_token, decode_refresh_token
from app.schemas.auth import Token


def test_refresh_token_settings_and_schema_are_available():
    token = create_refresh_token("user-1", tenant_id="tenant-1")
    payload = decode_refresh_token(token)
    schema = Token(access_token="access", refresh_token=token, token_type="bearer", user={})

    assert settings.JWT_REFRESH_SECRET
    assert settings.JWT_REFRESH_EXPIRE_DAYS >= 1
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "tenant-1"
    assert schema.refresh_token == token


def test_search_all_noa_delegates_to_search_noa(monkeypatch):
    calls = []

    def fake_search_noa(self, tender_id="", entity="", days=30):
        calls.append({"tender_id": tender_id, "entity": entity, "days": days})
        return [{"tender_id": tender_id, "entity": entity}]

    monkeypatch.setattr(eGPClient, "search_noa", fake_search_noa)
    client = eGPClient(timeout=1)

    result = client.search_all_noa(keyword="1302995", size=25)

    assert result == [{"tender_id": "1302995", "entity": ""}]
    assert calls == [{"tender_id": "1302995", "entity": "", "days": 25}]
