from app.services.ppr_ml_service import PPRMLService


def test_high_risk_leakage_candidate_is_rejected():
    bundle = {
        "summary": {
            "audit": {
                "risk_level": "high",
                "warnings": ["Validation metrics indicate feature leakage"],
            }
        }
    }

    assert PPRMLService._bundle_is_trusted(bundle) is False


def test_low_risk_candidate_is_accepted():
    bundle = {
        "summary": {
            "audit": {
                "risk_level": "low",
                "warnings": [],
            },
            "recommendation": "Use model-assisted ranking with rule-engine gate",
            "validation": {
                "win": {"n": 100, "positive_rate": 0.2, "auc": 0.7}
            },
        }
    }

    assert PPRMLService._bundle_is_trusted(bundle) is True
