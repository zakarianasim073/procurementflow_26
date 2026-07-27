export { useChatModels, useSendMessage } from './chat'
export { useAgents, useRunAgent } from './agents'
export { useRegisteredAgents, useBrainStatus, useRecentAgentRuns, usePipelinePhases } from './agents'
export * from './feedback'

export { useExecutiveOverview, useExecutivePipeline, useExecutiveReport, useLiveMetrics, usePredictionsModelStatus } from './executive'
export { useTenderSearch, useTenderDetail, useTenderBrainDetail } from './tender'
export { useTenderRadar, useRecentAgentResults, useAgencies, useCrawlerStatus, useOpeningReports } from './opportunity'
export { useCapabilities, useAuditLogs, useTenantInfo, useTeamMembers, useRoles } from './enterprise'
export { useMonitorStats, useMonitorAlerts, useWatchdogHealth, useWatchdogErrors, useMonitoringSources, useSystemMetrics, useEndpointHealth, useWatchdogAlerts, useHealthScore, useErrorTrends, useCheckEndpoints } from './monitoring'
export { useContractorCapacity, useContractorFinance, useTenderRecommendation, useTenderTDSCriteria } from './qualification'
export { useClauses, useClause, useClauseSearch, useRelatedClauses } from './clause'
export { useClauseTree, useClauseTags } from './clauseTree'
export { useRuleGraph, useRelationship, useRuleClusters } from './ruleGraph'
export { useExecutiveRoi, usePartnerMetrics, exportRoiDownload } from './roi'
export * from './contractor'
export * from './pricing'

// Knowledge Platform market intelligence
export {
  useMarketOverview,
  useAwardHistory,
  useAgencyBehaviour,
  useTopContractors,
  useNppiAnalysis,
} from './marketIntel'

// Pre-computed intelligence (clean_intel_* datasets)
export { useIntelCatalogue, useIntelDataset } from './cleanIntel'

// Phase 2 API Integration
// NOTE: no WebSocket hook is exported — the backend has no /api/ws endpoint yet.
// shared/ws/ holds the client-side scaffolding for when one is added.
export { useDocumentList, useDocumentUpload, useDocumentExtraction } from './documents'
// `useTeamMembers` is already exported from ./enterprise, so the Phase 2 one is aliased.
export { useTeam, useTeamMembers as usePhase2TeamMembers, useInviteTeamMember } from './team'
// `useAuditLogs` is already exported from ./enterprise, so the Phase 2 one is aliased.
export { useAdminStats, useAuditLogs as useAdminAuditLogs, useSystemHealth } from './admin'

// Acquisition (TEN) workspace hooks
export { useBoqResult, useBoqUpload, useBoqCompare, useBoqBrainCompare, useBoqJobStatus, useBoqJobResult, useBoqHistory } from './boq'
export { useComplianceCheck, useTdsCriteria, useRunComplianceCheck } from './compliance'
export { useCompetitors, useCompetitorAnalysis } from './competitor'
export { useSubmissions, useSubmissionTimeline, useUpdateSubmissionStatus } from './submission'
export { useAwards, useAwardStats } from './award'

// Knowledge (KNOW) workspace hooks
export { useSorSearch, useSorAgencies, useSorCompare } from './sor'

// Intelligence v2 hooks (curated frontend widgets)
export { usePprRules, useFaq, useCourses, useMarketTrends, usePricingScenarios, useWinRate, useKnowledgeSearch, useCategories } from './intelligence'