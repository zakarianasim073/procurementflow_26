import { useState } from 'react'
import { FileText, MapPin, Building2, Calendar, DollarSign, RefreshCw } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence, Tab } from '@widgets/shared'
import { Badge } from '@shared/ui/Badge'

const TABS: Tab[] = [
  { id: 'details', label: 'Details' },
  { id: 'documents', label: 'Documents' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'requirements', label: 'Requirements' },
]

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'Tender data from e-GP portal', status: 'verified', detail: 'Tender ID 1298004' },
]

export function TenderOverviewWidget() {
  const [activeTab, setActiveTab] = useState('details')
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <WidgetContainer>
      <WidgetHeader title="Tender Overview" subtitle="Complete tender details" icon={<FileText size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<RefreshCw size={14} />} label="Sync" />
        <ToolbarButton icon={<Calendar size={14} />} label="Timeline" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetContent>
        {activeTab === 'details' && (
          <div className="p-4 space-y-3">
            <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-900 dark:text-white">e-GP ID: 1298004</span>
                <Badge variant="outline" className="text-[10px] text-green-600 border-green-200">Live</Badge>
              </div>
              <p className="text-[11px] text-gray-500 mb-2">Rehabilitation of embankment from Ch 10.00km to 15.00km</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { icon: Building2, label: 'Agency', value: 'BWDB' },
                  { icon: MapPin, label: 'Location', value: 'Sirajganj' },
                  { icon: Calendar, label: 'Closing', value: 'Aug 15, 2026' },
                  { icon: DollarSign, label: 'Budget', value: '৳ 8.4 Cr' },
                ].map(({ icon: Icon, label, value }) => (
                  <div key={label} className="flex items-center gap-1.5">
                    <Icon size={12} className="text-gray-400" />
                    <div>
                      <p className="text-[10px] text-gray-400">{label}</p>
                      <p className="text-xs font-medium text-gray-900 dark:text-white">{value}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </WidgetContent>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Analyze Tender" />
      <WidgetFooter>
        <div className="text-[11px] text-gray-500">Last updated: 5 min ago</div>
      </WidgetFooter>
      <TrustPanel widgetId="tender-overview" widgetTitle="Tender Overview" confidence={92} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Tender Overview" />
    </WidgetContainer>
  )
}
