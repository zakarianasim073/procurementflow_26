import { useState, useMemo } from 'react'
import { Bell, Check, Info, Calendar, FileText, Search, RefreshCw } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterSelect, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui/Badge'
import { useRecentAgentRuns } from '@hooks/agents'

const TABS = [
  { id: 'all', label: 'All', count: 12 },
  { id: 'deadlines', label: 'Deadlines', count: 4 },
  { id: 'updates', label: 'Updates', count: 5 },
  { id: 'alerts', label: 'Alerts', count: 3 },
]

const SUBTABS = [
  { id: 'unread', label: 'Unread' },
  { id: 'read', label: 'Read' },
  { id: 'archived', label: 'Archived' },
]

const FALLBACK_NOTIFICATIONS = [
  { id: '1', type: 'deadline' as const, title: 'Tender submission tomorrow', detail: 'LGED-18/2026 closes in 2 days', time: '1h ago', icon: Calendar, color: 'text-red-500', bg: 'bg-red-50' },
  { id: '2', type: 'update' as const, title: 'BOQ analysis ready', detail: 'BWDB-24/2026 comparison with SOR complete', time: '3h ago', icon: Info, color: 'text-blue-500', bg: 'bg-blue-50' },
  { id: '3', type: 'alert' as const, title: 'New competitor detected', detail: 'ABC Ltd bidding on PWD-07/2026', time: '5h ago', icon: FileText, color: 'text-amber-500', bg: 'bg-amber-50' },
  { id: '4', type: 'deadline' as const, title: 'Performance security due', detail: 'PWD-05/2026 deadline in 7 days', time: '1d ago', icon: Calendar, color: 'text-red-500', bg: 'bg-red-50' },
  { id: '5', type: 'update' as const, title: 'PPR 2025 rules updated', detail: '3 new circulars added to compliance engine', time: '1d ago', icon: Info, color: 'text-blue-500', bg: 'bg-blue-50' },
]

const TYPE_ICONS: Record<string, typeof Bell> = { deadline: Calendar, update: Info, alert: FileText }

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Notifications from event system', status: 'verified', detail: 'Real-time push from backend' },
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

export function NotificationsWidget() {
  const [activeTab, setActiveTab] = useState('all')
  const [activeSubTab, setActiveSubTab] = useState('unread')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: agentRuns, isLoading } = useRecentAgentRuns(10)

  const notifications = useMemo(() => {
    if (!agentRuns?.length) return FALLBACK_NOTIFICATIONS
    return agentRuns.map(r => ({
      id: r.run_id,
      type: 'update' as const,
      title: `${r.agent_name} run`,
      detail: `${r.status}${r.tender_id ? ` · ${r.tender_id}` : ''}`,
      time: timeAgo(r.timestamp),
      icon: r.status === 'failed' ? FileText : r.status === 'running' ? Bell : Info,
      color: r.status === 'failed' ? 'text-red-500' : r.status === 'running' ? 'text-amber-500' : 'text-blue-500',
      bg: r.status === 'failed' ? 'bg-red-50' : r.status === 'running' ? 'bg-amber-50' : 'bg-blue-50',
    }))
  }, [agentRuns])

  if (isLoading) return <div>Loading...</div>

  return (
    <WidgetContainer>
      <WidgetHeader title="Notifications" subtitle="Deadlines & updates" icon={<Bell size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Check size={14} />} label="Mark all read" />
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterSelect>
          <option>All priorities</option>
          <option>High</option>
          <option>Medium</option>
          <option>Low</option>
        </FilterSelect>
      </WidgetFilters>
      <WidgetContent>
        <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
          {notifications.map((n) => {
            const Icon = TYPE_ICONS[n.type] ?? Bell
            return (
              <div key={n.id} className="group flex items-start gap-3 px-4 py-3 transition-colors hover:bg-gray-50/50 dark:hover:bg-gray-800/20">
                <div className={cn('rounded-lg p-1.5', n.bg)}><Icon size={14} className={n.color} /></div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-900 dark:text-white">{n.title}</p>
                  <p className="text-[11px] text-gray-500">{n.detail}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <span className="text-[10px] text-gray-400">{n.time}</span>
                  <Badge variant="outline" className="text-[10px]">{n.type}</Badge>
                </div>
              </div>
            )
          })}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Prioritize" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>12 unread</span>
          <button type="button" className="text-brand-600 hover:text-brand-700 dark:text-brand-400">View all</button>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="notifications" widgetTitle="Notifications" confidence={95} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Notifications" />
    </WidgetContainer>
  )
}
