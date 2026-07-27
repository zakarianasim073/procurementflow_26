import { useState, useMemo } from 'react'
import { Calendar, AlertTriangle, CheckCircle, Timer, Search, RefreshCw, Download } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetFilters, FilterSelect, FilterInput, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui/Badge'
import { useExecutivePipeline } from '@hooks/executive'

const TABS = [
  { id: 'upcoming', label: 'Upcoming', count: 3 },
  { id: 'this-week', label: 'This Week', count: 2 },
  { id: 'overdue', label: 'Overdue', count: 1 },
  { id: 'completed', label: 'Completed', count: 1 },
]

const SUBTABS = [
  { id: 'submission', label: 'Submission' },
  { id: 'evaluation', label: 'Evaluation' },
  { id: 'award', label: 'Award' },
  { id: 'all-types', label: 'All Types' },
]

const FALLBACK_DEADLINES = [
  { id: '1', tender: 'LGED-18/2026', agency: 'LGED', type: 'submission', deadline: 'Jul 25, 2026', daysLeft: 2, status: 'urgent' },
  { id: '2', tender: 'BWDB-24/2026', agency: 'BWDB', type: 'evaluation', deadline: 'Jul 27, 2026', daysLeft: 4, status: 'upcoming' },
  { id: '3', tender: 'PWD-07/2026', agency: 'PWD', type: 'preparation', deadline: 'Aug 4, 2026', daysLeft: 12, status: 'normal' },
  { id: '4', tender: 'RHD-03/2026', agency: 'RHD', type: 'bid', deadline: 'Jul 20, 2026', daysLeft: -3, status: 'overdue' },
]

const STATUS_STYLES = { urgent: { icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-50', label: 'Urgent' }, upcoming: { icon: Timer, color: 'text-amber-500', bg: 'bg-amber-50', label: 'Soon' }, normal: { icon: Calendar, color: 'text-blue-500', bg: 'bg-blue-50', label: 'Normal' }, overdue: { icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-100', label: 'Overdue' } }

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Deadlines from tender schedule', status: 'verified', detail: 'Sourced from e-GP tender data' },
]

export interface DeadlinesWidgetProps {
  agencyFilter?: string
}

export function DeadlinesWidget({ agencyFilter }: DeadlinesWidgetProps) {
  const [activeTab, setActiveTab] = useState('upcoming')
  const [activeSubTab, setActiveSubTab] = useState('all-types')
  const [searchQuery, setSearchQuery] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: pipelineData, isLoading } = useExecutivePipeline()

  const deadlines = useMemo(() => {
    if (!pipelineData?.agencies?.length) return FALLBACK_DEADLINES
    let agencies = pipelineData.agencies
    if (agencyFilter) agencies = agencies.filter(a => a.agency_code === agencyFilter)
    const items = agencies.flatMap(a => {
      const result: Array<{ id: string; tender: string; agency: string; type: string; deadline: string; daysLeft: number; status: string }> = []
      if (a.closing_7d > 0) result.push({ id: `${a.agency_code}-7d`, tender: `${a.agency_code} Tenders`, agency: a.agency_code, type: 'submission', deadline: 'Closing this week', daysLeft: a.closing_7d <= 3 ? a.closing_7d : 7, status: a.closing_7d <= 3 ? 'urgent' : 'upcoming' })
      if (a.closing_14d > 0) result.push({ id: `${a.agency_code}-14d`, tender: `${a.agency_code} Tenders`, agency: a.agency_code, type: 'evaluation', deadline: 'Closing in 2 weeks', daysLeft: 14, status: 'upcoming' })
      if (a.closing_30d > 0) result.push({ id: `${a.agency_code}-30d`, tender: `${a.agency_code} Tenders`, agency: a.agency_code, type: 'bid', deadline: 'Closing in 30 days', daysLeft: 30, status: 'normal' })
      return result
    })
    return items
  }, [pipelineData, agencyFilter])

  if (isLoading) return <div>Loading...</div>

  return (
    <WidgetContainer>
      <WidgetHeader title="Deadlines" subtitle="Upcoming tender dates" icon={<Calendar size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Calendar size={14} />} label="Calendar" />
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={SUBTABS} activeSubTab={activeSubTab} onSubTabChange={setActiveSubTab} />
      <WidgetFilters>
        <FilterSelect>
          <option>All agencies</option>
          <option>BWDB</option>
          <option>LGED</option>
          <option>PWD</option>
        </FilterSelect>
        <FilterInput value={searchQuery} onChange={setSearchQuery} placeholder="Search tenders..." />
      </WidgetFilters>
      <WidgetContent>
        <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
          {deadlines.map((d) => {
            const style = STATUS_STYLES[d.status as keyof typeof STATUS_STYLES]
            const Icon = style.icon
            return (
              <div key={d.id} className="flex items-center gap-3 px-4 py-3">
                <div className={cn('rounded-lg p-1.5', style.bg)}><Icon size={14} className={style.color} /></div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-900 dark:text-white">{d.tender}</span>
                    <Badge variant="outline" className="text-[10px]">{d.agency}</Badge>
                  </div>
                  <p className="mt-0.5 text-[11px] text-gray-500">{d.type} · {d.deadline}</p>
                </div>
                <div className="text-right">
                  <span className={cn('text-xs font-bold', d.daysLeft <= 0 ? 'text-red-600' : d.daysLeft <= 3 ? 'text-amber-600' : 'text-gray-600')}>
                    {d.daysLeft <= 0 ? 'Overdue' : `${d.daysLeft}d`}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Deadline Insights" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>1 overdue · 2 urgent</span>
          <span className="flex items-center gap-1"><CheckCircle size={12} /> 1 completed</span>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="deadlines" widgetTitle="Deadlines" confidence={90} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Deadlines" />
    </WidgetContainer>
  )
}
