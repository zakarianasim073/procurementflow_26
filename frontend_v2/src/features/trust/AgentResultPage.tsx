import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Bot } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { useRecentAgentResults } from '@hooks/index'
import type { AgentResultItem } from '@entities/index'
import {
  AiTrustPanel,
  ConfidenceMeter,
  EvidenceTimeline,
  ReasoningPanel,
  PromptBox,
  StreamingResponse,
  AgentActivity,
  ThinkingIndicator,
  SourceViewer,
  VersionBadge,
  RecommendationCard,
  AiDock,
  AiDockTrigger,
} from '@widgets/ai/index'

interface EvidenceEntry {
  id: string
  source: string
  title: string
  excerpt?: string
  timestamp: string
  score?: number
}

interface SourceDocument {
  id: string
  name: string
  type?: string
  url?: string
  excerpt?: string
}

interface AgentRun {
  id: string
  agentName: string
  status: 'running' | 'completed' | 'failed'
  startedAt: string
  summary?: string
}

/** Map a run's status to a TrustPanel verdict — status is real, so the verdict is honest. */
function verdictForStatus(status: string): 'passed' | 'warning' | 'needs_review' | 'unavailable' {
  if (status === 'completed' || status === 'success') return 'passed'
  if (status === 'failed' || status === 'error') return 'warning'
  if (status === 'running' || status === 'pending') return 'needs_review'
  return 'unavailable'
}

/** Read an optional numeric field from the agent's output payload. */
function num(output: Record<string, unknown> | undefined, key: string): number | undefined {
  const v = output?.[key]
  return typeof v === 'number' ? v : undefined
}

/** Build evidence entries from output.evidence when the agent provides it. */
function evidenceFrom(run: AgentResultItem): EvidenceEntry[] {
  const raw = run.output?.evidence
  if (!Array.isArray(raw)) return []
  return raw.flatMap((e, i): EvidenceEntry[] => {
    if (!e || typeof e !== 'object') return []
    const o = e as Record<string, unknown>
    return [{
      id: String(o.id ?? `${run.run_id}-ev-${i}`),
      source: String(o.source ?? run.agent_name),
      title: String(o.title ?? o.label ?? `Evidence ${i + 1}`),
      excerpt: typeof o.excerpt === 'string' ? o.excerpt : undefined,
      timestamp: String(o.timestamp ?? run.timestamp),
      score: typeof o.score === 'number' ? o.score : undefined,
    }]
  })
}

/** Build source documents from output.sources when present. */
function sourcesFrom(run: AgentResultItem): SourceDocument[] {
  const raw = run.output?.sources
  if (!Array.isArray(raw)) return []
  return raw.flatMap((s, i): SourceDocument[] => {
    if (!s || typeof s !== 'object') return []
    const o = s as Record<string, unknown>
    return [{
      id: String(o.id ?? `${run.run_id}-src-${i}`),
      name: String(o.name ?? o.title ?? `Source ${i + 1}`),
      type: typeof o.type === 'string' ? o.type : undefined,
      url: typeof o.url === 'string' ? o.url : undefined,
      excerpt: typeof o.excerpt === 'string' ? o.excerpt : undefined,
    }]
  })
}

export function AgentResultPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [dockOpen, setDockOpen] = useState(false)
  const { data, isLoading } = useRecentAgentResults(50)

  const run = data?.results.find((r) => r.run_id === runId)

  const header = (
    <div className="flex items-center gap-3">
      <button
        onClick={() => navigate('/trust/agents')}
        className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
        aria-label="Back to agents"
      >
        <ArrowLeft size={18} />
      </button>
      <div>
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
          {run ? run.agent_name : 'Agent Result'}
        </h1>
        <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
          {run ? `${run.run_id} · ${new Date(run.timestamp).toLocaleString()}` : `Run ${runId}`}
        </p>
      </div>
    </div>
  )

  if (isLoading) {
    return (
      <ScreenTemplate
        header={header}
        primary={
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-40 w-full rounded-xl" />
            ))}
          </div>
        }
      />
    )
  }

  if (!run) {
    return (
      <ScreenTemplate
        header={header}
        primary={
          <EmptyState
            title="Run not found"
            description={`No recent agent run matches ${runId}. It may have expired from the recent-results window.`}
          />
        }
      />
    )
  }

  const confidence = num(run.output, 'confidence') // 0–100 when the agent supplies it
  const evidence = evidenceFrom(run)
  const sources = sourcesFrom(run)
  const version = typeof run.output?.version === 'string' ? (run.output.version as string) : undefined
  const reasoning = typeof run.output?.reasoning === 'string' ? (run.output.reasoning as string) : undefined
  const responseText = run.output
    ? JSON.stringify(run.output, null, 2)
    : run.error
      ? `Error: ${run.error}`
      : 'No structured output returned by this agent.'

  // Other recent runs → real AgentActivity feed
  const activity: AgentRun[] = (data?.results ?? [])
    .filter((r) => r.run_id !== run.run_id)
    .slice(0, 6)
    .map((r) => ({
      id: r.run_id,
      agentName: r.agent_name,
      status: r.status === 'running' ? 'running' : r.status === 'failed' || r.status === 'error' ? 'failed' : 'completed',
      startedAt: r.timestamp,
      summary: r.tender_id ? `Tender ${r.tender_id}` : undefined,
    }))

  return (
    <ScreenTemplate
      header={header}
      kpiStrip={
        <div className="flex gap-3 overflow-x-auto pb-2">
          <div className="shrink-0 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <p className="text-xs text-gray-500">Status</p>
            <p className="mt-1 text-lg font-bold capitalize text-gray-900 dark:text-white">{run.status}</p>
          </div>
          <div className="shrink-0 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <p className="text-xs text-gray-500">Execution Time</p>
            <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{(run.execution_time_ms / 1000).toFixed(2)}s</p>
          </div>
          <div className="shrink-0 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <p className="text-xs text-gray-500">Tender</p>
            <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{run.tender_id ?? '—'}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
            <span className="font-mono text-xs text-gray-500">{run.agent_id}</span>
            {version && <VersionBadge version={version} />}
          </div>
        </div>
      }
      primary={
        <div className="space-y-6">
          {/* Trust + confidence (verdict from real status; confidence only when the agent reports it) */}
          <div className="grid gap-6 lg:grid-cols-2">
            <AiTrustPanel verdict={verdictForStatus(run.status)} confidence={confidence}>
              {run.status === 'completed' || run.status === 'success'
                ? 'Agent completed successfully. Evidence and sources below reflect what the agent returned.'
                : run.status === 'running' || run.status === 'pending'
                  ? 'Agent is still working — results are not yet final.'
                  : `Agent did not complete cleanly${run.error ? `: ${run.error}` : '.'}`}
            </AiTrustPanel>
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Confidence</p>
              {confidence != null ? (
                <ConfidenceMeter value={confidence} label="Agent confidence" />
              ) : (
                <p className="text-xs text-gray-500 dark:text-gray-400">This agent did not report a confidence score.</p>
              )}
            </div>
          </div>

          {run.status === 'running' && <ThinkingIndicator label={`${run.agent_name} is working…`} />}

          {/* Recommendation — only when the agent output includes a recognized decision */}
          {run.output?.recommendation === 'Bidding Recommended' && confidence != null && (
            <RecommendationCard decision="Bidding Recommended" confidence={confidence} />
          )}

          {/* Reasoning */}
          <ReasoningPanel title="Reasoning">
            {reasoning ?? 'No explicit reasoning trace was returned by this agent run.'}
          </ReasoningPanel>

          {/* Evidence + sources (each renders its own empty state when the agent gave none) */}
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Evidence Trail</p>
            <EvidenceTimeline entries={evidence} />
          </div>
          <SourceViewer sources={sources} />

          {/* Raw output */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Agent Output</p>
            <StreamingResponse content={responseText} isStreaming={run.status === 'running'} />
          </div>

          {/* Follow-up prompt — routes to the Trust chat with the assistant */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Ask a follow-up</p>
            <PromptBox
              placeholder={`Ask about ${run.agent_name}'s result…`}
              onSubmit={() => navigate('/trust/chat')}
            />
          </div>

          {/* Real recent-activity feed */}
          <AgentActivity runs={activity} />
        </div>
      }
      activityTimeline={
        <div>
          <AiDockTrigger onClick={() => setDockOpen(true)} />
          <AiDock
            isOpen={dockOpen}
            onClose={() => setDockOpen(false)}
            context={run.tender_id ? { tenderId: run.tender_id } : undefined}
          />
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
            <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
              <Bot size={14} /> About this run
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Widgets above are driven by the agent&apos;s real returned payload. Fields the agent didn&apos;t
              provide (confidence, evidence, sources) show their unavailable state rather than placeholder values.
            </p>
          </div>
        </div>
      }
    />
  )
}
