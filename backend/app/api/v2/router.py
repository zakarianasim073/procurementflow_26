"""
v2 API Router — Central registry for all 21 v2 modules.
NOTE: main.py loads and mounts each module individually (not via this router).
This file serves as a complete manifest and alternative import point.
"""
from fastapi import APIRouter

from .admin import router as admin_router
from .analytics import router as analytics_router
from .benchmarking import router as benchmarking_router
from .chat import router as chat_router
from .clauses import router as clauses_router
from .contractor import router as contractor_router
from .contractor_documents import router as contractor_documents_router
from .documents import router as documents_router
from .enterprise import router as enterprise_router
from .feedback import router as feedback_router
from .intelligence_enrichment import router as intelligence_enrichment_router
from .market_intelligence import router as market_intelligence_router
from .market_trends import router as market_trends_router
from .monitoring import router as monitoring_router
from .opportunity import router as opportunity_router
from .predictions import router as predictions_router
from .pricing import router as pricing_router
from .roi import router as roi_router
from .rules import router as rules_router
from .sso import router as sso_router
from .team import router as team_router
from .tenders import router as tenders_router

router = APIRouter()

# Include all 24 v2 API routers (__init__.py and router.py excluded)
router.include_router(admin_router)
router.include_router(analytics_router)
router.include_router(benchmarking_router)
router.include_router(chat_router)
router.include_router(clauses_router)
router.include_router(contractor_router)
router.include_router(contractor_documents_router)
router.include_router(documents_router)
router.include_router(enterprise_router)
router.include_router(feedback_router)
router.include_router(intelligence_enrichment_router)
router.include_router(market_intelligence_router)
router.include_router(market_trends_router)
router.include_router(monitoring_router)
router.include_router(opportunity_router)
router.include_router(predictions_router)
router.include_router(pricing_router)
router.include_router(roi_router)
router.include_router(rules_router)
router.include_router(sso_router)
router.include_router(team_router)
router.include_router(tenders_router)
