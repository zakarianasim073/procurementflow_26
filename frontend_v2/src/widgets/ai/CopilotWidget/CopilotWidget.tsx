import { useState } from 'react'
import { Bot, MessageSquare, FileText, TrendingUp, Search, Shield, Send, Sparkles } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetContent, WidgetFooter, TrustPanel, AiDrawer, WidgetActions } from '@widgets/shared'
import type { TrustEvidence, Tab } from '@widgets/shared'

const TABS: Tab[] = [
  { id: 'ask', label: 'Ask', icon: <MessageSquare size={14} /> },
  { id: 'explain', label: 'Explain', icon: <FileText size={14} /> },
  { id: 'generate', label: 'Generate', icon: <Sparkles size={14} /> },
  { id: 'predict', label: 'Predict', icon: <TrendingUp size={14} /> },
  { id: 'review', label: 'Review', icon: <Search size={14} /> },
  { id: 'evidence', label: 'Evidence', icon: <Shield size={14} /> },
]

const SUGGESTIONS: Record<string, string[]> = {
  ask: ['What is our win rate on BWDB?', 'Which tenders close this week?', 'Show compliance issues for PWD-07'],
  explain: ['Why 94% AI score for BWDB-24?', 'Explain discount recommendation'],
  generate: ['Generate compliance summary', 'Create competitor briefing', 'Draft bid strategy'],
  predict: ['Expected win rate next quarter?', 'Predict H2 2026 pricing trends'],
  review: ['Review BOQ items for BWDB-24', 'Check TDS compliance', 'Validate SOR rates'],
  evidence: ['Find supporting docs for Rule 42', 'Show calculation evidence'],
}

const EVIDENCE: TrustEvidence[] = [
  { id: 'ev-1', label: 'AI responses from procurement engine', status: 'verified', detail: 'v2.4.1 model' },
]

export function CopilotWidget() {
  const [activeTab, setActiveTab] = useState('ask')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [query, setQuery] = useState('')

  return (
    <WidgetContainer>
      <WidgetHeader title="AI Copilot" subtitle="Intelligent procurement assistant" icon={<Bot size={16} />} />
      <WidgetToolbar>
        <ToolbarButton icon={<Sparkles size={14} />} label="Suggest" />
        <ToolbarButton icon={<Sparkles size={14} />} label="Auto" />
      </WidgetToolbar>
      <WidgetTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetContent>
        <div className="flex flex-col h-full">
          <div className="flex-1 p-4">
            <p className="text-[11px] font-medium text-gray-500 mb-2">Suggestions</p>
            <div className="space-y-1">
              {(SUGGESTIONS[activeTab] ?? SUGGESTIONS.ask).map((s) => (
                <button key={s} type="button" className="w-full text-left rounded-md px-3 py-2 text-xs text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white transition-colors">
                  {s}
                </button>
              ))}
            </div>
          </div>
          <div className="border-t border-gray-100 p-3 dark:border-gray-800">
            <div className="flex items-center gap-2">
              <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask about tenders..." className="flex-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs placeholder-gray-400 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" />
              <button type="button" className="rounded-md bg-brand-500 p-2 text-white hover:bg-brand-600"><Send size={14} /></button>
            </div>
          </div>
        </div>
      </WidgetContent>
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span>Powered by Tender Intelligence Engine</span>
          <span className="flex items-center gap-1"><Sparkles size={12} /> v2.4</span>
        </div>
      </WidgetFooter>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Copilot Analysis" />
      <TrustPanel widgetId="copilot" widgetTitle="AI Copilot" confidence={93} evidence={EVIDENCE} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="AI Copilot" />
    </WidgetContainer>
  )
}
