import { lazy, Suspense, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AppShell, NotFoundScreen } from '@layouts/index'
import { LEGACY_REDIRECTS } from '@shared/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { bootstrapAuth } from '@entities/bootstrapAuth'
import { getAuthToken } from '@entities/authToken'

const _DashboardPage = lazy(() => import('@features/dashboard/DashboardPage').then(m => ({ default: m.DashboardPage })))
const ExecutivePage = lazy(() => import('@features/executive/ExecutivePage').then(m => ({ default: m.ExecutivePage })))
const PipelinePage = lazy(() => import('@features/executive/PipelinePage').then(m => ({ default: m.PipelinePage })))
const LoginPage = lazy(() => import('@features/auth/AuthPages').then(m => ({ default: m.LoginPage })))
const OidcCallbackPage = lazy(() => import('@features/auth/OIDCCallbackPage').then(m => ({ default: m.OIDCCallbackPage })))
const SamlCallbackPage = lazy(() => import('@features/auth/SAMLCallbackPage').then(m => ({ default: m.SAMLCallbackPage })))
const SettingsPage = lazy(() => import('@features/settings/SettingsPage').then(m => ({ default: m.SettingsPage })))
const TenderListPage = lazy(() => import('@features/tender/TenderListPage').then(m => ({ default: m.TenderListPage })))
const TenderDetailPage = lazy(() => import('@features/tender/TenderDetailPage').then(m => ({ default: m.TenderDetailPage })))
const TenderWorkspacePage = lazy(() => import('@features/tender/ProfessionalTenderWorkspace').then(m => ({ default: m.ProfessionalTenderWorkspace })))
const DiscoveryPage = lazy(() => import('@features/opportunity-discovery/DiscoveryPage').then(m => ({ default: m.DiscoveryPage })))
const QualificationPage = lazy(() => import('@features/opportunity-qualification/QualificationPage').then(m => ({ default: m.QualificationPage })))
const MonitoringPage = lazy(() => import('@features/opportunity-monitoring/MonitoringPage').then(m => ({ default: m.MonitoringPage })))
const TrustChatPage = lazy(() => import('@features/trust/TrustChatPage').then(m => ({ default: m.TrustChatPage })))
const TrustAgentsPage = lazy(() => import('@features/trust/TrustAgentsPage').then(m => ({ default: m.TrustAgentsPage })))
const AgentResultPage = lazy(() => import('@features/trust/AgentResultPage').then(m => ({ default: m.AgentResultPage })))
const KnowledgePage = lazy(() => import('@features/knowledge/KnowledgePage').then(m => ({ default: m.KnowledgePage })))
const IntelligenceExplorer = lazy(() => import('@features/intelligence').then(m => ({ default: m.IntelligenceExplorer })))
const FeedbackStatsPage = lazy(() => import('@features/knowledge/FeedbackStatsPage').then(m => ({ default: m.FeedbackStatsPage })))
const CompanyBrainPage = lazy(() => import('@features/knowledge/CompanyBrainPage').then(m => ({ default: m.CompanyBrainPage })))
const ClauseExplorer = lazy(() => import('@features/knowledge/ClauseExplorer').then(m => ({ default: m.ClauseExplorer })))
const RuleGraphPage = lazy(() => import('@features/knowledge/RuleGraphPage').then(m => ({ default: m.RuleGraphPage })))
const Ppr2025Page = lazy(() => import('@features/knowledge/Ppr2025Page').then(m => ({ default: m.Ppr2025Page })))
const EnterprisePage = lazy(() => import('@features/enterprise/EnterprisePage').then(m => ({ default: m.EnterprisePage })))
const RoiDashboard = lazy(() => import('@features/enterprise/RoiDashboard').then(m => ({ default: m.RoiDashboard })))
const PartnerDetailDashboard = lazy(() => import('@features/enterprise/PartnerDetailDashboard').then(m => ({ default: m.PartnerDetailDashboard })))
const AgentsPage = lazy(() => import('@features/admin/AgentsPage').then(m => ({ default: m.AgentsPage })))
const PricingLaboratory = lazy(() => import('@features/tender/PricingLaboratory').then(m => ({ default: m.PricingLaboratory })))

// TEN sub-pages
const BoqPage = lazy(() => import('@features/tender/BoqPage').then(m => ({ default: m.BoqPage })))
const CompliancePage = lazy(() => import('@features/tender/CompliancePage').then(m => ({ default: m.CompliancePage })))
const CompetitorsPage = lazy(() => import('@features/tender/CompetitorsPage').then(m => ({ default: m.CompetitorsPage })))
const SubmissionPage = lazy(() => import('@features/tender/SubmissionPage').then(m => ({ default: m.SubmissionPage })))
const AwardPage = lazy(() => import('@features/tender/AwardPage').then(m => ({ default: m.AwardPage })))

// KNOW sub-pages
const SorPage = lazy(() => import('@features/knowledge/SorPage').then(m => ({ default: m.SorPage })))
const KnowledgeAnalyticsPage = lazy(() => import('@features/knowledge/AnalyticsPage').then(m => ({ default: m.AnalyticsPage })))
const DocumentToolsPage = lazy(() => import('@features/knowledge/DocumentToolsPage').then(m => ({ default: m.DocumentToolsPage })))
const DocumentToolRunnerPage = lazy(() => import('@features/knowledge/DocumentToolRunnerPage').then(m => ({ default: m.DocumentToolRunnerPage })))
const LearningHubPage = lazy(() => import('@features/knowledge/LearningHubPage').then(m => ({ default: m.LearningHubPage })))
const KnowledgeSearchPage = lazy(() => import('@features/knowledge/KnowledgeSearchPage').then(m => ({ default: m.KnowledgeSearchPage })))

// Phase 3: New Features
const DocumentsPage = lazy(() => import('@features/documents/DocumentsPage').then(m => ({ default: m.DocumentsPage })))
const TeamPage = lazy(() => import('@features/team/TeamPage').then(m => ({ default: m.TeamPage })))
const AdminDashboard = lazy(() => import('@features/admin/AdminDashboard').then(m => ({ default: m.AdminDashboard })))

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
})

function RouteLoadingFallback() {
  return (
    <div className="flex flex-col gap-4 p-6" aria-live="polite" aria-busy="true">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-64" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  )
}

function RequireAuth() {
  const location = useLocation()
  if (getAuthToken()) return <AppShell />

  const redirect = encodeURIComponent(`${location.pathname}${location.search}`)
  return <Navigate to={`/login?redirect=${redirect}`} replace />
}

export default function App() {
  useEffect(() => { bootstrapAuth() }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Suspense fallback={<RouteLoadingFallback />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/sso/oidc/callback" element={<OidcCallbackPage />} />
            <Route path="/sso/saml/callback" element={<SamlCallbackPage />} />

            <Route element={<RequireAuth />}>
              {/* Executive */}
              <Route path="/executive" element={<ExecutivePage />} />
              <Route path="/executive/pipeline" element={<PipelinePage />} />

              {/* Tender - section routes BEFORE :id to avoid collision */}
              <Route path="/tender" element={<TenderListPage />} />
              <Route path="/tender/pricing" element={<PricingLaboratory />} />
              <Route path="/tender/:id/pricing-lab" element={<PricingLaboratory />} />
              {/* TEN sub-pages */}
              <Route path="/tender/boq" element={<BoqPage />} />
              <Route path="/tender/compliance" element={<CompliancePage />} />
              <Route path="/tender/competitors" element={<CompetitorsPage />} />
              <Route path="/tender/submission" element={<SubmissionPage />} />
              <Route path="/tender/award" element={<AwardPage />} />
              <Route path="/tender/:id" element={<TenderDetailPage />} />
              <Route path="/tender/:id/:panel" element={<TenderWorkspacePage />} />

              {/* Opportunity */}
              <Route path="/opportunity/discovery" element={<DiscoveryPage />} />
              <Route path="/opportunity/qualification" element={<QualificationPage />} />
              <Route path="/opportunity/qualification/:id" element={<QualificationPage />} />
              <Route path="/opportunity/monitoring" element={<MonitoringPage />} />

              {/* Trust */}
              <Route path="/trust/chat" element={<TrustChatPage />} />
              <Route path="/trust/agents" element={<TrustAgentsPage />} />
              <Route path="/trust/results/:runId" element={<AgentResultPage />} />

              {/* Knowledge - tab-routed sections */}
              <Route path="/knowledge/market" element={<KnowledgePage />} />
              <Route path="/knowledge/documents" element={<KnowledgePage />} />
              <Route path="/knowledge/analytics" element={<KnowledgePage />} />
              <Route path="/knowledge/feedback" element={<FeedbackStatsPage />} />
              <Route path="/knowledge/company/:companyId" element={<CompanyBrainPage />} />
              <Route path="/knowledge/clauses" element={<ClauseExplorer />} />
              <Route path="/knowledge/rule-graph" element={<RuleGraphPage />} />
              <Route path="/knowledge/ppr2025" element={<Ppr2025Page />} />
              <Route path="/knowledge/intelligence" element={<IntelligenceExplorer />} />
              {/* KNOW sub-pages */}
              <Route path="/knowledge/sor" element={<SorPage />} />
              <Route path="/knowledge/analytics-dashboard" element={<KnowledgeAnalyticsPage />} />
              <Route path="/knowledge/document-tools" element={<DocumentToolsPage />} />
              <Route path="/knowledge/document-tools/:tool" element={<DocumentToolRunnerPage />} />
              <Route path="/knowledge/learning" element={<LearningHubPage />} />
              <Route path="/knowledge/search" element={<KnowledgeSearchPage />} />
              <Route path="/knowledge" element={<Navigate to="/knowledge/market" replace />} />

              {/* User Settings */}
              <Route path="/settings" element={<SettingsPage />} />

              {/* Phase 3: Document Management */}
              <Route path="/documents" element={<DocumentsPage />} />

              {/* Phase 3: Team Management */}
              <Route path="/team" element={<TeamPage />} />

              {/* Admin */}
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/admin/agents" element={<AgentsPage />} />
              <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="/management" element={<Navigate to="/admin/dashboard" replace />} />

              {/* Enterprise - tab-routed sections */}
              <Route path="/enterprise/clients" element={<EnterprisePage />} />
              <Route path="/enterprise/team" element={<EnterprisePage />} />
              <Route path="/enterprise/rbac" element={<EnterprisePage />} />
              <Route path="/enterprise/settings" element={<EnterprisePage />} />
              <Route path="/enterprise/audit" element={<EnterprisePage />} />
              <Route path="/enterprise/roi" element={<RoiDashboard />} />
              <Route path="/enterprise/roi/:companyId" element={<PartnerDetailDashboard />} />
              <Route path="/enterprise" element={<Navigate to="/enterprise/clients" replace />} />

              {/* Workspace root → first section redirects */}
              <Route path="/opportunity" element={<Navigate to="/opportunity/discovery" replace />} />
              <Route path="/trust" element={<Navigate to="/trust/chat" replace />} />

              {/* Legacy redirects */}
              {Object.entries(LEGACY_REDIRECTS)
                .filter(([from, to]) => from !== to)
                .map(([from, to]) => (
                  <Route key={from} path={from} element={<Navigate to={to} replace />} />
                ))}

              <Route path="*" element={<NotFoundScreen />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
