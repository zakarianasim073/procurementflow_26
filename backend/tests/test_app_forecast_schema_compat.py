from __future__ import annotations

from app.agents.intelligence.app_forecast import APPForecastAgent


def test_app_forecast_amount_expr_prefers_existing_schema_column(monkeypatch):
    agent = APPForecastAgent()

    def fake_query(sql, params=None):
        if "information_schema.columns" in sql:
            return [("estimated_cost_bdt",)]
        return []

    monkeypatch.setattr(agent, "_query", fake_query)

    assert agent._amount_expr() == "COALESCE(estimated_cost_bdt, 0)"


def test_app_forecast_amount_expr_uses_zero_when_no_amount_column(monkeypatch):
    agent = APPForecastAgent()
    monkeypatch.setattr(agent, "_query", lambda sql, params=None: [])

    assert agent._amount_expr() == "0"
