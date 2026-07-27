import { useState, useMemo } from 'react'
import { ClipboardList, TrendingUp, TrendingDown, Download, RefreshCw, Search } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetSubTabs, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence, Tab } from '@widgets/shared'
import { useBoqResult } from '@hooks/boq'
import type { BoqItem } from '@entities/boq/types'

const TABS: Tab[] = [
  { id: 'comparison', label: 'Comparison' },
  { id: 'items', label: 'Items' },
  { id: 'summary', label: 'Summary' },
  { id: 'rates', label: 'SOR Rates' },
  { id: 'discrepancies', label: 'Discrepancies' },
  { id: 'history', label: 'History' },
]

const AGENCY_TABS: Tab[] = [
  { id: 'BWDB', label: 'BWDB' },
  { id: 'PWD', label: 'PWD' },
  { id: 'LGED', label: 'LGED' },
  { id: 'ALL', label: 'All Agencies' },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'BOQ parsed from uploaded PDF', status: 'verified', detail: 'pdfplumber extraction' },
  { id: 'ev-2', label: 'SOR rates from PPR database', status: 'verified', detail: '1024 BWDB items' },
]

export interface BOQWidgetProps {
  tenderId?: string
}

export function BOQWidget({ tenderId }: BOQWidgetProps) {
  const [activeTab, setActiveTab] = useState('comparison')
  const [agencyTab, setAgencyTab] = useState('ALL')
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data: result, isLoading } = useBoqResult(tenderId ?? '')
  const items: BoqItem[] = result?.items ?? []

  const aboveCount = useMemo(() => items.filter((i) => i.flag === 'above').length, [items])
  const belowCount = useMemo(() => items.filter((i) => i.flag === 'below').length, [items])

  return (
    <WidgetContainer>
      <WidgetHeader title="BOQ Comparison" subtitle="Item-level rate analysis against SOR" icon={<ClipboardList size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Download size={14} />} label="Export" />
        <ToolbarButton icon={<Search size={14} />} label="Search" />
        <ToolbarButton icon={<RefreshCw size={14} />} label="Refresh" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetSubTabs subtabs={AGENCY_TABS} activeSubTab={agencyTab} onSubTabChange={setAgencyTab} />
      <WidgetContent>
        <div className="p-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-32"><p className="text-sm text-gray-500">Loading BOQ data...</p></div>
          ) : items.length === 0 ? (
            <div className="flex items-center justify-center h-32"><p className="text-sm text-gray-500">{tenderId ? 'No BOQ data found' : 'Select a tender to view BOQ comparison'}</p></div>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100 dark:border-gray-800">
                  <th className="text-left font-medium text-gray-500 pb-2">Code</th>
                  <th className="text-left font-medium text-gray-500 pb-2">Description</th>
                  <th className="text-center font-medium text-gray-500 pb-2">Unit</th>
                  <th className="text-right font-medium text-gray-500 pb-2">Qty</th>
                  <th className="text-right font-medium text-gray-500 pb-2">SOR Rate</th>
                  <th className="text-right font-medium text-gray-500 pb-2">BOQ Rate</th>
                  <th className="text-right font-medium text-gray-500 pb-2">Diff</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => {
                  const sorRate = item.sor_rate ?? 0
                  const boqRate = item.rate ?? 0
                  const diff = item.diff ?? (boqRate - sorRate)
                  const status = item.flag ?? (diff > 0 ? 'above' : 'below')
                  return (
                    <tr key={item.code ?? i} className="border-b border-gray-50 dark:border-gray-800/50">
                      <td className="py-2 font-mono text-gray-900 dark:text-white">{item.code ?? item.item_no ?? '-'}</td>
                      <td className="py-2 text-gray-700 dark:text-gray-300">{item.desc}</td>
                      <td className="py-2 text-center text-gray-500">{item.unit}</td>
                      <td className="py-2 text-right">{(item.qty ?? 0).toLocaleString()}</td>
                      <td className="py-2 text-right font-medium">{sorRate.toFixed(2)}</td>
                      <td className="py-2 text-right font-medium">{boqRate.toFixed(2)}</td>
                      <td className="py-2 text-right">
                        <span className={`inline-flex items-center gap-0.5 font-medium ${status === 'above' ? 'text-red-600' : 'text-green-600'}`}>
                          {status === 'above' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                          {diff > 0 ? '+' : ''}{diff.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Analyze BOQ" />
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>{items.length} items compared</span>
          {aboveCount + belowCount > 0 && (
            <span className="flex items-center gap-1"><TrendingUp size={12} className="text-red-500" /> {aboveCount} above, {belowCount} below SOR</span>
          )}
        </div>
      </WidgetFooter>
      <TrustPanel widgetId="boq" widgetTitle="BOQ Comparison" confidence={94} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="BOQ Comparison" />
    </WidgetContainer>
  )
}
