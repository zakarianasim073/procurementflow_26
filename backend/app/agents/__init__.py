"""Procurement Flow Specialist BD — Agent System
Specialized agents organized by capability domain.
"""
from .core.base import BaseAgent, AgentResult, AgentStatus
from .core.brain import AgentBrain, BrainMessage, AgentCapability
from .core.llm import LLMService, LLMResponse, BaseLLMProvider
from .core.memory import AgentMemoryService
from .core.vector_db import VectorDBService, RAGService, EmbeddingService

# Discovery
from .discovery import TenderRadarAgent, TenderAcquisitionAgent, CorrigendumWatchdogAgent, VisionIntelligenceAgent, MaterialPriceCrawlerAgent, MaterialMarginAnalyzerAgent

# Evaluation
from .evaluation import PPREvaluationAgent, PPR2025ComplianceAgent, LERTPredictionAgent, EligibilityComplianceAgent, RiskIntelligenceAgent, DataQualityValidatorAgent

# Intelligence
from .intelligence import BOQIntelligenceAgent, SpecIntelligenceAgent, AwardIntelligenceAgent, ResourceCapacityAgent, APPForecastAgent, ChangeDetectionAgent

# Pricing
from .pricing import MarketRateIntelligenceAgent, RateAnalysisAgent, RABillPredictorAgent, VatTaxCalculatorAgent, EGPRateFillAgent, SORZoneMatcherAgent

# Competitor
from .competitor import WinProbabilityAgent, BidPositionOptimizerAgent, CompetitorIntelligenceAgent, CompetitorPricingPredictorAgent, SyndicateRadarAgent

# Decision
from .decision import FinancialIntelligenceAgent, ExecutiveDecisionAgent, AIBidAssistantAgent, BidNoBidAgent, ClientIntelligenceAgent

# Acquisition
from .acquisition import DocumentPreparationAgent, DocumentAIAgent, TenderDocumentAgent, SubmissionValidationAgent, TenderPreparationAgent, TenderDashboardAgent, OpeningReportAgent

# Knowledge & Learning
from .knowledge import KnowledgeLakeAgent, ReportGenerationAgent, CompanyBrainAgent, MarketBrainAgent
from .learning import LearningAgent

# Pre-emptive Intelligence (New)
from .competitor import MoatSLTAnalyzerAgent
from .evaluation import PPR2025DashboardAgent
from .discovery import TenderPreScreenerAgent
from .decision.client_intelligence import ClientIntelligenceAgent

# Legacy agents (still needed)
from .registry import AgentRegistry
from .orchestrator import WorkflowOrchestrator
from .portal_explorer import PortalExplorer
from .whatsapp_agent import WhatsAppAutomationAgent

__all__ = [
    "BaseAgent", "AgentResult", "AgentStatus", "AgentBrain", "BrainMessage", "AgentCapability",
    "LLMService", "LLMResponse", "BaseLLMProvider",
    "AgentMemoryService",
    "VectorDBService", "RAGService", "EmbeddingService",
    "TenderRadarAgent", "TenderAcquisitionAgent", "CorrigendumWatchdogAgent", "VisionIntelligenceAgent",
    "BOQIntelligenceAgent", "SpecIntelligenceAgent", "AwardIntelligenceAgent", "ResourceCapacityAgent",
    "PPREvaluationAgent", "PPR2025ComplianceAgent", "LERTPredictionAgent", "EligibilityComplianceAgent", "RiskIntelligenceAgent",
    "MarketRateIntelligenceAgent", "RateAnalysisAgent", "RABillPredictorAgent", "VatTaxCalculatorAgent", "EGPRateFillAgent",
    "WinProbabilityAgent", "BidPositionOptimizerAgent", "CompetitorIntelligenceAgent", "CompetitorPricingPredictorAgent", "SyndicateRadarAgent",
    "FinancialIntelligenceAgent", "ExecutiveDecisionAgent", "AIBidAssistantAgent",
    "DocumentPreparationAgent", "DocumentAIAgent", "TenderDocumentAgent", "SubmissionValidationAgent", "TenderPreparationAgent", "TenderDashboardAgent", "OpeningReportAgent",
    "KnowledgeLakeAgent", "ReportGenerationAgent", "LearningAgent",
    "MoatSLTAnalyzerAgent", "PPR2025DashboardAgent", "TenderPreScreenerAgent", "SORZoneMatcherAgent", "BidNoBidAgent", "ClientIntelligenceAgent", "CompanyBrainAgent", "MarketBrainAgent", "APPForecastAgent", "DataQualityValidatorAgent", "ChangeDetectionAgent",
    "AgentRegistry", "WorkflowOrchestrator", "PortalExplorer", "WhatsAppAutomationAgent",
]

# Watchdog & Error Intelligence
from app.agents.core.watchdog import AgentWatchdog, get_watchdog

# Intelligence Engineer
from app.agents.core.engineer import IntelligenceEngineer, get_engineer
