import { useState } from 'react'
import { Bot, MessageSquare, FileText, TrendingUp, Search, Shield, Send, Sparkles } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetToolbar, ToolbarButton, WidgetTabs, WidgetContent, WidgetFooter, TrustPanel, AiDrawer } from '@widgets/shared'
import { Badge } from '@shared/ui/Badge'
import { useRecentAgentRuns } from '@hooks/index'

const DOCK_TABS = [
  { id: 'ask', label: 'Ask', icon: <MessageSquare size={14} /> },
  { id: 'explain', label: 'Explain', icon: <FileText size={14} /> },
  { id: 'generate', label: 'Generate', icon: <Sparkles size={14} /> },
  { id: 'predict', label: 'Predict', icon: <TrendingUp size={14} /> },
  { id: 'review', label: 'Review', icon: <Search size={14} /> },
  { id: 'evidence', label: 'Evidence', icon: <Shield size={14} /> },
]

const SUGGESTIONS: Record<string, string[]> = {
  ask: ['What is our win rate on BWDB tenders?', 'Which tenders close this week?', 'Show me compliance issues for PWD-07'],
  explain: ['Why was the AI score for BWDB-24 94%?', 'Explain the discount recommendation', 'Break down the compliance warning'],
  generate: ['Generate a compliance summary report', 'Create a competitor briefing', 'Draft a bid strategy document'],
  predict: ['What is our expected win rate next quarter?', 'Predict pricing trends for H2 2026', 'Forecast capacity utilization'],
  review: ['Review BOQ items for BWDB-24', 'Check TDS compliance', 'Validate SOR rates for LGED-18'],
  evidence: ['Find supporting docs for Rule 42', 'Show calculation evidence', 'Verify award references'],
}

const RESPONSES: Record<string, { answer: string; confidence: number; sources: string[] }> = {
  'What is our win rate on BWDB tenders?': {
    answer: 'Your win rate on BWDB tenders is 43% (14 wins out of 33 bids over the last 2 years). This is above the industry average of 38% for BWDB contracts.',
    confidence: 95,
    sources: ['Award Records (2024-2026)', 'Competitor Intelligence DB', 'Win Rate Analytics'],
  },
  'Why was the AI score for BWDB-24 94%?': {
    answer: 'The AI score of 94% for BWDB-24/2026 is driven by: 1) 92% capability match with your equipment & personnel, 2) 88% historical win similarity, 3) Strong financial position for the ৳2.1 Cr bond requirement.',
    confidence: 97,
    sources: ['Capability Matrix', 'Historical Win Analysis', 'Financial Health Report'],
  },
}

const QUICK_ACTIONS = [
  { label: 'Analyze Tender', icon: Search },
  { label: 'Check Compliance', icon: Shield },
  { label: 'Compare BOQ', icon: FileText },
  { label: 'Price Strategy', icon: TrendingUp },
]

export function AiDockWidget() {
  const [activeTab, setActiveTab] = useState('ask')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeResponse, setActiveResponse] = useState<string | null>(null)
  const { data: runsRes } = useRecentAgentRuns(20)
  const responseData = activeResponse ? RESPONSES[activeResponse as keyof typeof RESPONSES] : null
  const suggestions = SUGGESTIONS[activeTab] ?? SUGGESTIONS.ask

  const evidenceItems = (runsRes ?? []).slice(0, 5).map((r, i) => ({
    id: `ev-run-${i}`,
    label: `${r.agent_name ?? r.agent_id}: ${r.status}`,
    status: r.status === 'success' ? 'verified' as const : 'warning' as const,
    detail: r.execution_time_ms ? `${(r.execution_time_ms / 1000).toFixed(1)}s` : 'completed',
  }))

  const handleSuggestion = (s: string) => {
    setQuery(s)
    setActiveResponse(s in RESPONSES ? s : null)
  }

  return (
    <WidgetContainer>
      <WidgetHeader title="AI Assistant" subtitle="Intelligent procurement copilot" icon={<Bot size={16} />} />
      <WidgetToolbar>
        {QUICK_ACTIONS.map((action) => {
          const Icon = action.icon
          return <ToolbarButton key={action.label} icon={<Icon size={14} />} label={action.label} />
        })}
      </WidgetToolbar>
      <WidgetTabs tabs={DOCK_TABS} activeTab={activeTab} onTabChange={setActiveTab} />

      <WidgetContent>
        <div className="flex flex-col h-full">
          {responseData ? (
            <div className="flex-1 space-y-3 p-4">
              <div className="rounded-lg border border-brand-100 bg-brand-50/50 p-3 dark:border-brand-900/20 dark:bg-brand-900/5">
                <div className="flex items-center gap-2 mb-1.5">
                  <Sparkles size={14} className="text-brand-500" />
                  <span className="text-xs font-medium text-brand-700 dark:text-brand-400">AI Response</span>
                  <Badge variant="outline" className="text-[10px] ml-auto">Confidence: {responseData.confidence}%</Badge>
                </div>
                <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">{responseData.answer}</p>
              </div>
              <div>
                <p className="text-[11px] font-medium text-gray-500 mb-1.5">Sources</p>
                <div className="flex flex-wrap gap-1.5">
                  {responseData.sources.map((src) => (
                    <Badge key={src} variant="outline" className="text-[10px]">{src}</Badge>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 p-4">
              <p className="text-[11px] font-medium text-gray-500 mb-2">Suggestions</p>
              <div className="space-y-1">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => handleSuggestion(s)}
                    className="w-full text-left rounded-md px-3 py-2 text-xs text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="border-t border-gray-100 p-3 dark:border-gray-800">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask anything about your tenders..."
                className="flex-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs placeholder-gray-400 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
                onKeyDown={(e) => e.key === 'Enter' && handleSuggestion(query)}
              />
              <button type="button" className="rounded-md bg-brand-500 p-2 text-white hover:bg-brand-600 transition-colors">
                <Send size={14} />
              </button>
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
      <TrustPanel widgetId="ai-dock" widgetTitle="AI Assistant" confidence={93} evidence={evidenceItems} />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="AI Assistant" />
    </WidgetContainer>
  )
}
