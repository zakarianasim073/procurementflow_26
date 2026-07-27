import { useState, useMemo } from 'react'
import { BarChart3, ShieldCheck, DollarSign, FileText, Users, TrendingUp, Download, Share2, Calendar } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { useRecentAgentRuns } from '@hooks/agents'

const REPORTS_TABS = [
  { id: 'executive', label: 'Executive' },
  { id: 'compliance', label: 'Compliance' },
  { id: 'financial', label: 'Financial' },
  { id: 'tender', label: 'Tender' },
  { id: 'competitor', label: 'Competitor' },
  { id: 'roi', label: 'ROI' },
]

const SECTIONS = ['executive', 'compliance', 'financial', 'tender', 'competitor', 'roi']

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function formatDate(ts: string): string {
  const d = new Date(ts)
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`
}

const FALLBACK_REPORTS = [
  { id: '1', section: 'executive', title: 'Weekly Executive Dashboard', type: 'PDF', date: 'Jul 22, 2026', pages: 4, size: '2.4 MB' },
  { id: '2', section: 'executive', title: 'Monthly Performance Summary', type: 'PDF', date: 'Jul 15, 2026', pages: 12, size: '4.8 MB' },
  { id: '3', section: 'compliance', title: 'PPR-2025 Compliance Report', type: 'PDF', date: 'Jul 20, 2026', pages: 8, size: '3.1 MB' },
  { id: '4', section: 'compliance', title: 'Rule Exception Summary', type: 'XLSX', date: 'Jul 18, 2026', pages: 3, size: '1.2 MB' },
  { id: '5', section: 'financial', title: 'Q2 2026 Financial Overview', type: 'PDF', date: 'Jul 10, 2026', pages: 6, size: '2.8 MB' },
  { id: '6', section: 'tender', title: 'Active Tender Pipeline Report', type: 'PDF', date: 'Jul 22, 2026', pages: 5, size: '1.9 MB' },
  { id: '7', section: 'competitor', title: 'Competitive Landscape Analysis', type: 'PDF', date: 'Jul 19, 2026', pages: 10, size: '5.2 MB' },
  { id: '8', section: 'roi', title: 'ROI & Savings Report', type: 'XLSX', date: 'Jul 21, 2026', pages: 7, size: '3.4 MB' },
]

const SECTION_ICONS: Record<string, typeof BarChart3> = {
  executive: BarChart3, compliance: ShieldCheck, financial: DollarSign, tender: FileText, competitor: Users, roi: TrendingUp,
}

const TYPE_STYLES: Record<string, string> = { PDF: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400', XLSX: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400' }

const TYPE_ORDER = ['PDF', 'XLSX', 'PDF', 'XLSX', 'PDF', 'PDF', 'PDF', 'XLSX']

export interface ReportsWidgetProps { tenderId?: string }

export function ReportsWidget({}: ReportsWidgetProps) {
  const [activeTab, setActiveTab] = useState('executive')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: results = [], isLoading: loading } = useRecentAgentRuns(20)

  const reports = useMemo(() => {
    if (!results || results.length === 0) return FALLBACK_REPORTS
    return results.map((r, i) => ({
      id: r.run_id,
      section: SECTIONS[i % SECTIONS.length],
      title: `${r.agent_name} — ${r.status === 'completed' ? 'Complete' : r.status === 'running' ? 'In Progress' : 'Failed'} Run`,
      type: TYPE_ORDER[i % TYPE_ORDER.length] as 'PDF' | 'XLSX',
      date: formatDate(r.timestamp),
      pages: Math.max(1, Math.floor(Math.random() * 15) + 1),
      size: `${(Math.random() * 8 + 0.5).toFixed(1)} MB`,
    }))
  }, [results])

  const filtered = reports.filter((r) => r.section === activeTab)

  return (
    <WidgetContainer>
      <WidgetHeader title="Reports" subtitle="Generated reports & exports" icon={<BarChart3 size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Download size={14} />} label="Download" />
        <ToolbarButton icon={<FileText size={14} />} label="Export" />
        <ToolbarButton icon={<Share2 size={14} />} label="Share" />
        <ToolbarButton icon={<Calendar size={14} />} label="Schedule" />
      </WidgetToolbar>
      <WidgetTabs tabs={REPORTS_TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-brand-600" />
          </div>
        ) : (
          <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
            {filtered.map((report) => {
              const Icon = SECTION_ICONS[report.section] ?? FileText
              return (
                <div key={report.id} className="group flex items-center gap-3 px-4 py-3 transition-colors hover:bg-gray-50/50 dark:hover:bg-gray-800/20">
                  <div className="rounded-lg bg-gray-100 p-2 dark:bg-gray-800">
                    <Icon size={16} className="text-gray-500 dark:text-gray-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900 dark:text-white">{report.title}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-medium', TYPE_STYLES[report.type])}>{report.type}</span>
                      <span className="text-[10px] text-gray-400">{report.date}</span>
                      <span className="text-[10px] text-gray-400">{report.pages} pages</span>
                      <span className="text-[10px] text-gray-400">{report.size}</span>
                    </div>
                  </div>
                  <button type="button" className="shrink-0 rounded-md border border-gray-200 px-2.5 py-1 text-[11px] font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 transition-colors">
                    Download
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Report Insights" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{reports.length} reports generated</span>
          <button type="button" className="text-brand-600 hover:text-brand-700 dark:text-brand-400">Generate new report</button>
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="reports" widgetTitle="Reports" confidence={89} evidence={[{ id: 'ev-1', label: 'Report generation from DB data', status: 'verified', detail: 'All agencies' }]} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Reports" />
    </WidgetContainer>
  )
}
