export * from './shared'
export * from './executive'
export * from './tender'
export * from './opportunity'
export * from './compliance'
export * from './evidence'
// Explicit re-exports from ./ai to avoid ambiguous RecommendationCard (also in ./executive)
export {
  AgentActivity,
  AiDock,
  AiDockTrigger,
  AiDockWidget,
  ConfidenceMeter,
  EvidenceTimeline,
  PromptBox,
  ReasoningPanel,
  SourceViewer,
  StreamingResponse,
  ThinkingIndicator,
  AiTrustPanel,
  VersionBadge,
  CopilotWidget,
  AgentStatus,
} from './ai'

export * from './company-brain'
export * from './competitor'
export * from './pricing'
export * from './reports'
export * from './trust-panel'
