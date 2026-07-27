def test_agent_server_imports_with_canonical_settings():
    import app.agents.server

    assert app.agents.server.app.version
