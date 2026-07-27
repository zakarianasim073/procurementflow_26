import { useNavigate, useLocation } from 'react-router-dom'
import { BarChart3, FileText, TrendingUp } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@shared/ui/Tabs'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { useLiveMetrics, useRecentAgentRuns } from '@hooks/index'
import { MarketResearchPanel } from './MarketResearchPanel'

const TABS = [
  { id: 'market', label: 'Market Research', icon: TrendingUp },
  { id: 'documents', label: 'Document Tools', icon: FileText },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
] as const

type TabId = typeof TABS[number]['id']

function tabFromPath(path: string): TabId {
  if (path.includes('/documents')) return 'documents'
  if (path.includes('/analytics')) return 'analytics'
  return 'market'
}

function pathForTab(tab: TabId): string {
  if (tab === 'market') return '/knowledge/market'
  if (tab === 'documents') return '/knowledge/documents'
  return '/knowledge/analytics'
}

function DocumentToolsPanel() {
  const { data: runsRes } = useRecentAgentRuns(5)
  const recentTools = (runsRes ?? []).slice(0, 3)

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Document Tools</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <button type="button" onClick={() => window.location.assign('/knowledge/document-tools/resume')} className="rounded-lg border border-gray-100 bg-gray-50 p-4 text-left hover:border-blue-300 dark:border-gray-700 dark:bg-gray-800/60">
            <FileText className="mb-2 h-8 w-8 text-blue-500" />
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">Resume Generator</h3>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Generate contractor resumes from company data</p>
          </button>
          <button type="button" onClick={() => window.location.assign('/knowledge/document-tools/vat-tax')} className="rounded-lg border border-gray-100 bg-gray-50 p-4 text-left hover:border-green-300 dark:border-gray-700 dark:bg-gray-800/60">
            <BarChart3 className="mb-2 h-8 w-8 text-green-500" />
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">VAT/Tax Calculator</h3>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Calculate VAT and tax implications for tender pricing</p>
          </button>
        </div>
        {recentTools.length > 0 && (
          <div className="mt-3 border-t border-gray-100 pt-3 dark:border-gray-700">
            <p className="mb-2 text-xs font-medium text-gray-500">Recently used agents</p>
            <div className="space-y-1">
              {recentTools.map((r, i) => (
                <div key={r.run_id ?? i} className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
                  <span>{r.agent_name ?? r.agent_id}</span>
                  <span className={r.status === 'success' ? 'text-green-500' : 'text-amber-500'}>{r.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function AnalyticsPanel() {
  const metrics = useLiveMetrics()

  if (metrics.isLoading) return <Skeleton className="h-64 w-full rounded-xl" />

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Market Analytics</h2>
        {metrics.data?.top_agencies ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                <p className="text-xs text-gray-500">Total Tenders</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">{metrics.data.overview.total_tenders.toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                <p className="text-xs text-gray-500">Market Value</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  ৳{(metrics.data.overview.total_value_bdt / 1e7).toLocaleString(undefined, { maximumFractionDigits: 0 })}Cr
                </p>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                <p className="text-xs text-gray-500">Awarded</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">{metrics.data.overview.awarded_count.toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                <p className="text-xs text-gray-500">Top Contractors</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">{metrics.data.top_contractors?.length ?? 0}</p>
              </div>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase text-gray-500">Top Agencies</h3>
                <div className="space-y-1">
                  {metrics.data.top_agencies.slice(0, 5).map((agency) => (
                    <div key={agency.agency_code} className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
                      <span>{agency.agency_name || agency.agency_code}</span>
                      <span>{agency.tender_count.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase text-gray-500">Top Contractors</h3>
                <div className="space-y-1">
                  {metrics.data.top_contractors.slice(0, 5).map((contractor) => (
                    <div key={contractor.contractor_name} className="flex justify-between gap-3 text-xs text-gray-600 dark:text-gray-400">
                      <span className="truncate">{contractor.contractor_name}</span>
                      <span className="shrink-0">{contractor.award_count.toLocaleString()} awards</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <EmptyState title="No analytics data" description="Analytics data will appear when tenders are tracked." />
        )}
      </div>
    </div>
  )
}

export function KnowledgePage() {
  const location = useLocation()
  const navigate = useNavigate()
  const activeTab = tabFromPath(location.pathname)

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Knowledge Platform</h1>
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">Market research, document tools, and analytics</p>
        </div>
      }
      primary={
        <Tabs value={activeTab} onValueChange={(v) => navigate(pathForTab(v as TabId), { replace: true })}>
          <TabsList>
            {TABS.map(t => (
              <TabsTrigger key={t.id} value={t.id}>
                <t.icon className="h-4 w-4 mr-2" />
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
          <TabsContent value="market"><MarketResearchPanel /></TabsContent>
          <TabsContent value="documents"><DocumentToolsPanel /></TabsContent>
          <TabsContent value="analytics"><AnalyticsPanel /></TabsContent>
        </Tabs>
      }
    />
  )
}
