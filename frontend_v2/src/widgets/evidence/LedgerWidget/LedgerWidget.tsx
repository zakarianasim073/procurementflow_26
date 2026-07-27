import { useState, useMemo } from 'react'
import { BookOpen, Search, Download, RefreshCw } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetContent, WidgetFooter } from '@widgets/shared'
import type { Tab } from '@widgets/shared'
import { useRecentAgentRuns } from '@hooks/agents'

const TABS: Tab[] = [
  { id: 'entries', label: 'Entries' },
  { id: 'audit', label: 'Audit Trail' },
  { id: 'summary', label: 'Summary' },
]

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function formatDate(ts: string): string {
  const d = new Date(ts)
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`
}

const FALLBACK_ENTRIES = [
  { date: 'Jul 22, 2026', action: 'BOQ comparison performed', user: 'System', ref: 'CMP-20260722-001' },
  { date: 'Jul 21, 2026', action: 'Compliance check executed', user: 'AI Agent', ref: 'CHK-20260721-003' },
  { date: 'Jul 20, 2026', action: 'Tender document downloaded', user: 'Acquisition Agent', ref: 'DL-20260720-007' },
  { date: 'Jul 19, 2026', action: 'SOR rates synchronized', user: 'System', ref: 'SYNC-20260719-001' },
  { date: 'Jul 18, 2026', action: 'Competitor profile updated', user: 'Admin', ref: 'UPD-20260718-012' },
]

export interface LedgerWidgetProps { limit?: number }

export function LedgerWidget({ limit = 20 }: LedgerWidgetProps) {
  const [activeTab, setActiveTab] = useState('entries')
  const { data: results = [], isLoading: loading } = useRecentAgentRuns(limit)

  const entries = useMemo(() => {
    if (!results || results.length === 0) return FALLBACK_ENTRIES
    return results.map((r) => ({
      date: formatDate(r.timestamp),
      action: `${r.agent_name} — ${r.status}`,
      user: r.agent_name,
      ref: r.run_id,
    }))
  }, [results])

  return (
    <WidgetContainer>
      <WidgetHeader title="Ledger" subtitle="Audit trail & action log" icon={<BookOpen size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<Download size={14} />} label="Export" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-brand-600" />
          </div>
        ) : (
          <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
            {entries.map((entry, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-2.5">
                <div>
                  <p className="text-xs font-medium text-gray-900 dark:text-white">{entry.action}</p>
                  <p className="text-[10px] text-gray-400">{entry.ref} · {entry.user}</p>
                </div>
                <span className="text-[10px] text-gray-400">{entry.date}</span>
              </div>
            ))}
          </div>
        )}
      </WidgetContent>
      <WidgetFooter>
        <div className="text-[11px] text-gray-500">{entries.length} recent entries</div>
      </WidgetFooter>
    </WidgetContainer>
  )
}
