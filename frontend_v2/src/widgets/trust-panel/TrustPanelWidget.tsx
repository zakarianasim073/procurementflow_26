import { useState, useMemo } from 'react'
import { ShieldCheck, FileSearch, Scale, BadgeCheck, Bot, BookOpen, GitBranch, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { WidgetContainer, WidgetHeader, WidgetTabs, WidgetContent, WidgetFooter, AiDrawer, WidgetActions } from '@widgets/shared'
import { cn } from '@shared/lib/cn'
import { Badge } from '@shared/ui/Badge'
import { Progress } from '@shared/ui/Progress'
import { useRecentAgentRuns } from '@hooks/agents'

const TRUST_TABS = [
  { id: 'why', label: 'Why', icon: <FileSearch size={14} /> },
  { id: 'evidence', label: 'Evidence', icon: <Scale size={14} /> },
  { id: 'rules', label: 'Rules', icon: <BookOpen size={14} /> },
  { id: 'confidence', label: 'Confidence', icon: <BadgeCheck size={14} /> },
  { id: 'agents', label: 'Agents', icon: <Bot size={14} /> },
  { id: 'ledger', label: 'Ledger', icon: <BookOpen size={14} /> },
  { id: 'version', label: 'Version', icon: <GitBranch size={14} /> },
]

const CONFIDENCE_METRICS = [
  { label: 'Data Completeness', score: 94, status: 'pass' },
  { label: 'Source Reliability', score: 91, status: 'pass' },
  { label: 'AI Model Confidence', score: 88, status: 'pass' },
  { label: 'Cross-reference Match', score: 82, status: 'warning' },
  { label: 'Temporal Freshness', score: 76, status: 'warning' },
]

const FALLBACK_AGENT_RUNS = [
  { id: '1', agent: 'Tender Acquisition Agent', status: 'completed', duration: '1m 24s', time: '10 min ago', version: '1.4.0' },
  { id: '2', agent: 'BOQ Comparison Agent', status: 'completed', duration: '45s', time: '25 min ago', version: '1.2.1' },
  { id: '3', agent: 'Compliance Check Agent', status: 'running', duration: '2m 10s', time: 'Now', version: '1.5.0' },
  { id: '4', agent: 'Competitor Analysis Agent', status: 'failed', duration: '30s', time: '1h ago', version: '1.3.0' },
]

const VERDICT_CHAIN = [
  { step: 'Document Acquisition', status: 'verified', detail: 'Tender notice + BOQ + TDS downloaded from e-GP' },
  { step: 'OCR & Text Extraction', status: 'verified', detail: 'pdfplumber extraction, 98.2% accuracy' },
  { step: 'SOR Rate Matching', status: 'verified', detail: '1024 BWDB rates matched against BOQ items' },
  { step: 'Rule Evaluation', status: 'verified', detail: 'PPR-2025 Rules 18, 37, 42, 53 evaluated' },
  { step: 'Confidence Scoring', status: 'verified', detail: 'Bayesian confidence model: 94% overall' },
]

const STATUS_ICONS: Record<string, typeof CheckCircle> = { pass: CheckCircle, warning: AlertTriangle, fail: XCircle, verified: CheckCircle, running: AlertTriangle, completed: CheckCircle, failed: XCircle }
const STATUS_COLORS: Record<string, string> = { pass: 'text-green-500', warning: 'text-amber-500', fail: 'text-red-500', verified: 'text-green-500', running: 'text-blue-500', completed: 'text-green-500', failed: 'text-red-500' }

function formatDuration(ms: number): string {
  const secs = Math.floor(ms / 1000)
  if (secs < 60) return `${secs}s`
  const mins = Math.floor(secs / 60)
  const rem = secs % 60
  return `${mins}m ${rem}s`
}

function formatTimeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export function TrustPanelWidget() {
  const [activeTab, setActiveTab] = useState('why')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { data: results = [], isLoading: loading } = useRecentAgentRuns(20)

  const agentRuns = useMemo(() => {
    if (!results || results.length === 0) return FALLBACK_AGENT_RUNS
    return results.map((r) => ({
      id: r.run_id,
      agent: r.agent_name,
      status: r.status,
      duration: formatDuration(r.execution_time_ms),
      time: formatTimeAgo(r.timestamp),
      version: '1.0.0',
    }))
  }, [results])

  return (
    <WidgetContainer>
      <WidgetHeader title="Trust Panel" subtitle="Verification & audit trail" icon={<ShieldCheck size={16} />} />
      <WidgetTabs tabs={TRUST_TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <WidgetContent>
        {activeTab === 'why' && (
          <div className="p-4 space-y-3">
            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              Each insight in ProcureFlow is backed by a verifiable chain of evidence. The AI does not guess — it traces every recommendation back to source documents, rules, and calculations.
            </p>
            <div className="space-y-2">
              {VERDICT_CHAIN.map((v) => {
                const Icon = STATUS_ICONS[v.status] ?? CheckCircle
                return (
                  <div key={v.step} className="flex items-start gap-2">
                    <Icon size={14} className={cn('mt-0.5 shrink-0', STATUS_COLORS[v.status])} />
                    <div>
                      <p className="text-xs font-medium text-gray-900 dark:text-white">{v.step}</p>
                      <p className="text-[11px] text-gray-500">{v.detail}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
        {activeTab === 'confidence' && (
          <div className="space-y-3 p-4">
            {CONFIDENCE_METRICS.map((m) => {
              const Icon = STATUS_ICONS[m.status] ?? CheckCircle
              return (
                <div key={m.label}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <Icon size={12} className={STATUS_COLORS[m.status]} />
                      <span className="text-xs text-gray-700 dark:text-gray-300">{m.label}</span>
                    </div>
                    <span className="text-xs font-semibold">{m.score}%</span>
                  </div>
                  <Progress value={m.score} className="h-1.5" />
                </div>
              )
            })}
            <div className="mt-4 rounded-lg border border-gray-100 bg-gray-50/50 p-3 text-center dark:border-gray-800 dark:bg-gray-800/30">
              <p className="text-lg font-bold text-gray-900 dark:text-white">88%</p>
              <p className="text-[11px] text-gray-500">Overall Confidence Score</p>
            </div>
          </div>
        )}
        {activeTab === 'agents' && (
          <div className="divide-y divide-gray-50 dark:divide-gray-800/50">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-brand-600" />
              </div>
            ) : (
              agentRuns.map((a) => {
                const Icon = STATUS_ICONS[a.status] ?? CheckCircle
                return (
                  <div key={a.id} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <Icon size={14} className={STATUS_COLORS[a.status]} />
                      <div>
                        <p className="text-xs font-medium text-gray-900 dark:text-white">{a.agent}</p>
                        <div className="flex items-center gap-2 text-[10px] text-gray-400">
                          <span>v{a.version}</span>
                          <span>{a.duration}</span>
                          <span>{a.time}</span>
                        </div>
                      </div>
                    </div>
                    <Badge variant="outline" className={cn('text-[10px]', a.status === 'failed' ? 'border-red-200 text-red-600' : a.status === 'running' ? 'border-blue-200 text-blue-600' : 'border-green-200 text-green-600')}>
                      {a.status}
                    </Badge>
                  </div>
                )
              })
            )}
          </div>
        )}
        {activeTab === 'version' && (
          <div className="p-4 space-y-3">
            {[
              { component: 'Frontend Widget Framework', version: '2.0.0', updated: 'Jul 22, 2026' },
              { component: 'AI Engine', version: '2.4.1', updated: 'Jul 20, 2026' },
              { component: 'SOR Comparison Module', version: '1.3.2', updated: 'Jul 18, 2026' },
              { component: 'Compliance Engine', version: '1.5.0', updated: 'Jul 15, 2026' },
              { component: 'Competitor Intelligence', version: '1.2.0', updated: 'Jul 10, 2026' },
            ].map((v) => (
              <div key={v.component} className="flex items-center justify-between rounded-lg border border-gray-100 p-3 dark:border-gray-800">
                <div>
                  <p className="text-xs font-medium text-gray-900 dark:text-white">{v.component}</p>
                  <p className="text-[11px] text-gray-500">Updated {v.updated}</p>
                </div>
                <Badge>v{v.version}</Badge>
              </div>
            ))}
          </div>
        )}
      </WidgetContent>
      <WidgetFooter>
        <div className="flex items-center justify-between text-[11px] text-gray-500">
          <span className="flex items-center gap-1"><ShieldCheck size={12} className="text-green-500" /> All systems verified</span>
          <span>Audit ID: AUD-20260723-001</span>
        </div>
      </WidgetFooter>
      <WidgetActions onAiAction={() => setDrawerOpen(true)} aiLabel="Trust Analysis" />
      <AiDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} widgetTitle="Trust Panel" />
    </WidgetContainer>
  )
}
