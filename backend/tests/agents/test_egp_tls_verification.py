from app.agents.egp_client import eGPClient


def test_egp_client_enables_tls_certificate_verification(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("app.agents.egp_client.httpx.Client", FakeClient)

    _ = eGPClient().client

    assert captured["verify"] is True
