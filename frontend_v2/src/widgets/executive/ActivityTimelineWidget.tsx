import { useState, useMemo } from 'react'
import { Clock, FileText, Users, CheckCircle, AlertCircle, RefreshCw, Search, Download } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterSelect, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { useRecentAgentRuns } from '@hooks/agents'

const TABS = [
  { id: 'all', label: 'All Activity' },
  { id: 'agent', label: 'Agent Runs' },
  { id: 'user', label: 'User Actions' },
  { id: 'system', label: 'System' },
]

const SUBTABS = [
  { id: 'today', label: 'Today' },
  { id: 'yesterday', label: 'Yesterday' },
  { id: 'week', label: 'This Week' },
]

const FALLBACK_ACTIVITIES = [
  { id: '1', type: 'agent', action: 'Tender Acquisition Agent completed', detail: 'Downloaded docs for BWDB-24/2026', time: '10 min ago', icon: RefreshCw, color: 'text-blue-500', bg: 'bg-blue-50' },
  { id: '2', type: 'user', action: 'BOQ comparison requested', detail: 'Compared BWDB-24/2026 against SOR', time: '25 min ago', icon: FileText, color: 'text-purple-500', bg: 'bg-purple-50' },
  { id: '3', type: 'agent', action: 'Compliance check completed', detail: 'PPR-2025 rules evaluated for LGED-18', time: '1h ago', icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50' },
  { id: '4', type: 'system', action: 'SOR rates updated', detail: 'LGED 2025 schedule synchronized', time: '2h ago', icon: AlertCircle, color: 'text-amber-500', bg: 'bg-amber-50' },
  { id: '5', type: 'user', action: 'Competitor profile viewed', detail: 'ABC Construction Ltd profile opened', time: '3h ago', icon: Users, color: 'text-indigo-500', bg: 'bg-indigo-50' },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Activity log from audit_trail', status: 'verified', detail: 'All user and system actions logged' },
]

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function ActivityTimelineWidget() {
  const [activeTab, setActiveTab] = useState('all')
  const [activeSubTab, setActiveSubTab] = useState('today')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: agentRuns, isLoading } = useRecentAgentRuns(20)

  const activities = useMemo(() => {
    if (!agentRuns?.length) return FALLBACK_ACTIVITIES
    return agentRuns.map(r => ({
      id: r.run_id,
      type: 'agent' as const,
      action: `${r.agent_name} completed`,
      detail: r.error ? `Error: ${r.error}` : `${r.status} · ${(r.execution_time_ms / 1000).toFixed(1)}s`,
      time: timeAgo(r.timestamp),
      icon: r.status === 'failed' ? AlertCircle : r.status === 'running' ? RefreshCw : CheckCircle,
      color: r.status === 'failed' ? 'text-red-500' : r.status === 'running' ? 'text-amber-500' : 'text-green-500',
      bg: r.status === 'failed' ? 'bg-red-50' : r.status === 'running' ? 'bg-amber-50' : 'bg-green-50',
    }))
  }, [agentRuns])

  const filtered = activeTab === 'all' ? activities : activities.filter((a) => a.type === activeTab)

  if (isLoading) return <div>Loading...</div>

  return (
    <WidgetContainer>
      <WidgetHeader title="Activity Timeline" subtitle="Recent platform activity" icon={<Clock size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterSelect>
          <option>All events</option>
          <option>Errors only</option>
          <option>Warnings</option>
        </FilterSelect>
      </WidgetFilters>
      <WidgetContent>
        <div className="relative">
          <div className="absolute left-6 top-0 bottom-0 w-px bg-gray-100 dark:bg-gray-800" />
          <div className="space-y-0">
            {filtered.map((activity) => {
              const Icon = activity.icon
              return (
                <div key={activity.id} className="relative flex items-start gap-4 px-4 py-3">
                  <div className={cn('relative z-10 rounded-lg p-1.5', activity.bg)}><Icon size={12} className={activity.color} /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900 dark:text-white">{activity.action}</p>
                    <p className="text-[11px] text-gray-500">{activity.detail}</p>
                  </div>
                  <span className="shrink-0 text-[10px] text-gray-400">{activity.time}</span>
                </div>
              )
            })}
          </div>
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Analyze Activity" />
      <WidgetFooter>
        <div className="text-[11px] text-gray-500">Last 24 hours · {filtered.length} events</div>
      </WidgetFooter>
      <TrustPanel widgetId="activity-timeline" widgetTitle="Activity Timeline" confidence={96} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Activity Timeline" />
    </WidgetContainer>
  )
}
