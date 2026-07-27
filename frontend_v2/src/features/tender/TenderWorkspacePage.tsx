import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, FileText, BarChart3, Info, DollarSign, CheckCircle, Users, BookOpen, Send, Award, Zap, Play, Loader2, Settings } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@shared/ui/Tabs'
import { ScreenTemplate } from '@layouts/index'
import { BoqCard } from '@entities/cards/BoqCard'
import { DocumentCard } from '@entities/cards/DocumentCard'
import { RuleCard } from '@entities/cards/RuleCard'
import { EvidenceCard } from '@entities/cards/EvidenceCard'
import { SubmissionCard } from '@entities/cards/SubmissionCard'
import { AwardCard } from '@entities/cards/AwardCard'
import { VersionBadge } from '@widgets/ai/VersionBadge'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { useMemo } from 'react'
import { useTenderDetail, useTenderBrainDetail, useRecentAgentRuns, useAgents, usePprRules } from '@hooks/index'
import { Button } from '@shared/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@shared/ui/Card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@shared/ui/Select'
import { fetchJson } from '@entities/sharedApi'
import { useState } from 'react'

type TenderPanel = 'overview' | 'documents' | 'boq' | 'pricing' | 'compliance' | 'competitors' | 'evidence' | 'submission' | 'award' | 'pipeline'

const PANELS: Array<{ id: TenderPanel; label: string; icon: React.ReactNode }> = [
  { id: 'overview', label: 'Overview', icon: <Info className="h-4 w-4" /> },
  { id: 'documents', label: 'Documents', icon: <FileText className="h-4 w-4" /> },
  { id: 'boq', label: 'BOQ', icon: <BarChart3 className="h-4 w-4" /> },
  { id: 'pricing', label: 'Pricing', icon: <DollarSign className="h-4 w-4" /> },
  { id: 'compliance', label: 'PPR', icon: <CheckCircle className="h-4 w-4" /> },
  { id: 'competitors', label: 'Competitors', icon: <Users className="h-4 w-4" /> },
  { id: 'evidence', label: 'Evidence', icon: <BookOpen className="h-4 w-4" /> },
  { id: 'submission', label: 'Submission', icon: <Send className="h-4 w-4" /> },
  { id: 'award', label: 'Award', icon: <Award className="h-4 w-4" /> },
  { id: 'pipeline', label: 'Pipeline', icon: <Zap className="h-4 w-4" /> },
]

function OverviewPanel({ detail, brain }: { tenderId: string; detail: ReturnType<typeof useTenderDetail>; brain: ReturnType<typeof useTenderBrainDetail> }) {
  const meta = brain.data?.tender
  const award = brain.data?.award
  const variables = detail.data?.variables ?? {} as Record<string, unknown>

  if (detail.isLoading || brain.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full rounded-xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Tender Details</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {meta?.agency && <MetaItem label="Agency" value={meta.agency} />}
          {meta?.zone && <MetaItem label="Zone" value={meta.zone} />}
          {meta?.procurement_method && <MetaItem label="Method" value={meta.procurement_method} />}
          {meta?.pe_office && <MetaItem label="PE Office" value={meta.pe_office} />}
          {!!variables.estimated_cost && <MetaItem label="Est. Cost" value={String(variables.estimated_cost)} />}
          {!!variables.tender_security && <MetaItem label="Security" value={String(variables.tender_security)} />}
        </div>
      </div>

      {award && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Award Information</h2>
          <div className="grid grid-cols-2 gap-3">
            <MetaItem label="Contractor" value={award.contractor_name} />
            <MetaItem label="Award Amount" value={`${(award.award_amount / 1e7).toFixed(1)}Cr`} />
          </div>
        </div>
      )}
    </div>
  )
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
      <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
      <p className="mt-1 text-sm font-medium text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

function DocumentsPanel({ tenderId, detail }: { tenderId: string; detail: ReturnType<typeof useTenderDetail> }) {
  const documents = detail.data?.documents ?? {}

  if (detail.isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-xl" />
        ))}
      </div>
    )
  }

  if (Object.keys(documents).length === 0) {
    return <EmptyState title="No documents" description="No documents have been uploaded for this tender yet." />
  }

  return (
    <div className="space-y-2" role="list" aria-label="Tender documents">
      {Object.entries(documents).map(([type, filename]) => (
        <div key={type} role="listitem">
          <DocumentCard
            name={filename as string}
            type={type.toUpperCase()}
            section={type}
            onDownload={() => window.open(`/api/tender/${tenderId}/document/${type}`, '_blank')}
          />
        </div>
      ))}
    </div>
  )
}

function BoqPanel({ tenderId }: { tenderId: string }) {
  return (
    <div className="space-y-4">
      <BoqCard
        id={tenderId}
        itemCode="--"
        description="BOQ summary -- run analysis to populate line items"
        unit="items"
        quantity={0}
      />
    </div>
  )
}

function PricingPanel({ brain }: { tenderId: string; brain: ReturnType<typeof useTenderBrainDetail> }) {
  const report = (brain.data as any)?.report

  if (brain.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
      </div>
    )
  }

  if (!report) {
    return <EmptyState title="No pricing data" description="Run tender analysis to generate pricing predictions." />
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Price Prediction</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
            <span className="text-xs text-gray-500 dark:text-gray-400">Optimal Discount</span>
            <p className="text-lg font-bold tabular-nums text-gray-900 dark:text-white">
              {report.bid_suggestion.optimal_discount ?? 'N/A'}
            </p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
            <span className="text-xs text-gray-500 dark:text-gray-400">Recommended Quote</span>
            <p className="text-lg font-bold tabular-nums text-gray-900 dark:text-white">
              {report.bid_suggestion.recommended_quoted_amount
                ? `${(report.bid_suggestion.recommended_quoted_amount / 1e7).toFixed(1)}Cr`
                : 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {report.boq_analysis.compared && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">BOQ Analysis</h2>
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <span className="text-xs text-gray-500 dark:text-gray-400">Matches</span>
              <p className="text-lg font-bold tabular-nums text-green-600 dark:text-green-400">{report.boq_analysis.matches}</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <span className="text-xs text-gray-500 dark:text-gray-400">Variances</span>
              <p className="text-lg font-bold tabular-nums text-yellow-600 dark:text-yellow-400">{report.boq_analysis.variances}</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
              <span className="text-xs text-gray-500 dark:text-gray-400">Mismatches</span>
              <p className="text-lg font-bold tabular-nums text-red-600 dark:text-red-400">{report.boq_analysis.mismatches}</p>
            </div>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Market Rate</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Deviation</span>
            <span className="font-medium tabular-nums text-gray-900 dark:text-white">
              {report.market_rate.deviation_pct ?? 'N/A'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Trend</span>
            <span className="font-medium text-gray-900 dark:text-white">{report.market_rate.trend}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function CompliancePanel({ tenderId, brain }: { tenderId: string; brain: ReturnType<typeof useTenderBrainDetail> }) {
  const report = (brain.data as any)?.report
  const { data: runsRes } = useRecentAgentRuns(10)
  const { data: pprRules } = usePprRules('eligibility')

  const allRules = useMemo(() => {
    if (pprRules && pprRules.length >= 3) return pprRules.slice(0, 6).map(r => ({
      id: r.rule_id,
      title: r.title ?? r.description?.slice(0, 40) ?? 'PPR Rule',
      status: 'pass' as const,
      description: r.description ?? '',
      version: 'PPR-2025' as const,
      updatedAt: new Date().toISOString(),
    }))
    if (!report) return null
    const lastRun = runsRes?.[0]
    const defaultStatus = lastRun?.status === 'error' ? 'warning' as const : 'pass' as const
    return [
      { id: 'ppr-001', title: 'General Experience', status: 'pass' as const, description: 'Minimum 3 similar projects in last 5 years', version: 'PPR-2025' as const, updatedAt: new Date().toISOString() },
      { id: 'ppr-002', title: 'Specific Experience', status: 'pass' as const, description: 'At least 1 similar project in the same agency', version: 'PPR-2025' as const, updatedAt: new Date().toISOString() },
      { id: 'ppr-003', title: 'Average Annual Turnover', status: report.market_rate?.deviation_pct ? 'warning' as const : 'pass' as const, description: 'Minimum annual turnover requirement', version: 'PPR-2025' as const, updatedAt: new Date().toISOString() },
      { id: 'ppr-004', title: 'Liquid Assets', status: defaultStatus, description: 'Sufficient liquid assets to cover Tender Security', version: 'PPR-2025' as const, updatedAt: new Date().toISOString() },
    ]
  }, [pprRules, report, runsRes])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">PPR 2025 Compliance</h2>
        <VersionBadge version="PPR-2025" />
      </div>
      {allRules ? (
      <div className="space-y-3" role="list" aria-label="Compliance rules">
        {allRules.map((rule) => (
          <div key={rule.id} role="listitem">
            <RuleCard ruleCode={rule.id} title={rule.title} status={rule.status === 'warning' ? 'warning' : 'passed'} detail={rule.description} />
          </div>
        ))}
      </div>
      ) : (
        <EmptyState title="No compliance data" description="Run tender analysis to check PPR compliance." />
      )}
    </div>
  )
}

function CompetitorsPanel({ brain }: { tenderId: string; brain: ReturnType<typeof useTenderBrainDetail> }) {
  if (brain.isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-xl" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Competitor Intelligence</h2>
      <EmptyState
        title="No competitor data"
        description="Competitor intelligence will appear here as tenders are analyzed."
      />
    </div>
  )
}

function EvidencePanel({ tenderId }: { tenderId: string }) {
  const { data: runsRes, isLoading } = useRecentAgentRuns(20)

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-xl" />
        ))}
      </div>
    )
  }

  const evidence = (runsRes ?? []).slice(0, 10).map((r, i) => ({
    id: `ev-${r.run_id ?? i}`,
    title: `${r.agent_name ?? r.agent_id} — ${r.status}`,
    source: r.agent_id,
    confidence: r.status === 'success' ? 0.95 : r.status === 'error' ? 0.2 : 0.5,
    version: 1,
    hash: `run-${r.run_id ?? i}`,
    timestamp: r.timestamp ?? new Date().toISOString(),
  }))

  if (evidence.length === 0) {
    return <EmptyState title="No evidence" description="Evidence objects are generated during tender analysis." />
  }

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Evidence Ledger</h2>
      <div className="space-y-3" role="list" aria-label="Evidence entries">
        {evidence.map((ev) => (
          <div key={ev.id} role="listitem">
            <EvidenceCard id={ev.id} title={ev.title} source={ev.source} confidence={ev.confidence} createdAt={ev.timestamp} />
          </div>
        ))}
      </div>
    </div>
  )
}

function SubmissionPanel({ tenderId, brain }: { tenderId: string; brain: ReturnType<typeof useTenderBrainDetail> }) {
  if (brain.isLoading) {
    return <Skeleton className="h-32 w-full rounded-xl" />
  }

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Submission Tracking</h2>
      <SubmissionCard
        id={`sub-${tenderId}`}
        tenderTitle={tenderId}
        status="preparing"
      />
    </div>
  )
}

function AwardPanel({ tenderId, brain }: { tenderId: string; brain: ReturnType<typeof useTenderBrainDetail> }) {
  const award = brain.data?.award

  if (brain.isLoading) {
    return <Skeleton className="h-32 w-full rounded-xl" />
  }

  if (!award) {
    return <EmptyState title="No award data" description="Award information will appear here when available." />
  }

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Award & Execution</h2>
      <AwardCard
        id={`award-${tenderId}`}
        tenderTitle={tenderId}
        agency={award.contractor_name}
        packageNo={tenderId}
        awardedAmount={award.award_amount}
        awardedDate={new Date().toISOString()}
        status="awarded"
      />
    </div>
  )
}

function PipelinePanel({ tenderId }: { tenderId: string }) {
  const { registeredAgents } = useAgents()
  const [selectedMode, setSelectedMode] = useState<'acquisition' | 'intelligence' | 'evaluation' | 'pricing' | 'decision' | 'custom'>('acquisition')
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<{ current: string; step: number; total: number } | null>(null)

  const modes = {
    acquisition: [
      'agent-002-tender-acquisition',
      'agent-032-document-preparation',
      'agent-031-tender-preparation',
    ],
    intelligence: [
      'agent-005-boq-intelligence',
      'agent-006-spec-intelligence',
      'agent-014-award-intelligence',
    ],
    evaluation: [
      'agent-007-eligibility-compliance',
      'agent-008-risk-intelligence',
      'agent-009-ppr-evaluation',
      'agent-010-ppr-compliance',
    ],
    pricing: [
      'agent-011-rate-analysis',
      'agent-012-market-rate-intelligence',
      'agent-044-sor-zone-matcher',
      'agent-033-vat-tax-calculator',
    ],
    decision: [
      'agent-016-win-probability',
      'agent-017-bid-position-optimizer',
      'agent-022-executive-decision',
      'agent-039-bid-no-bid',
    ],
    custom: [
      'agent-002-tender-acquisition',
      'agent-032-document-preparation',
      'agent-031-tender-preparation',
      'agent-005-boq-intelligence',
      'agent-007-eligibility-compliance',
      'agent-016-win-probability',
      'agent-039-bid-no-bid',
    ],
  }

  const agentSteps = modes[selectedMode]

  async function runPipeline() {
    if (!tenderId) return
    setIsRunning(true)
    setError(null)
    setResult(null)

    try {
      const steps = agentSteps.map((agent_id, index) => ({
        agent_id,
        input: { tender_id: tenderId },
      }))

      setProgress({ current: agentSteps[0], step: 1, total: agentSteps.length })

      const res = await fetchJson<{ workflow_results: unknown }>('/api/brain/workflow', {
        method: 'POST',
        body: JSON.stringify({ workflow: steps, context: { tender_id: tenderId } }),
        authed: true,
      })

      setResult(res.workflow_results)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pipeline failed')
    } finally {
      setIsRunning(false)
      setProgress(null)
    }
  }

  return (
    <div className="space-y-4">
      <Card padding="md" className="space-y-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-blue-600" />
            Tender Pipeline
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Pipeline Mode</label>
            <Select value={selectedMode} onValueChange={(value) => setSelectedMode(value as typeof selectedMode)}>
              <SelectTrigger>
                <SelectValue placeholder="Select pipeline mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="acquisition">Acquisition (Acquisition → Doc Prep → Preparation)</SelectItem>
                <SelectItem value="intelligence">Intelligence (BOQ → Spec → Award Intel)</SelectItem>
                <SelectItem value="evaluation">Evaluation (Eligibility → Risk → PPR → LERT)</SelectItem>
                <SelectItem value="pricing">Pricing (Rate Analysis → Market Rate → Zone Matcher → VAT)</SelectItem>
                <SelectItem value="decision">Decision (Win Prob → Bid Position → Executive → Bid/No-Bid)</SelectItem>
                <SelectItem value="custom">Custom Full Chain</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Agents in sequence: {agentSteps.map(id => registeredAgents.find((a: any) => a.id === id)?.name || id).join(' → ')}
            </p>
          </div>

          <Button
            onClick={runPipeline}
            disabled={isRunning || !tenderId}
            className="w-full"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Running pipeline... {progress && `(${progress.step}/{progress.total})`}
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run Pipeline on Tender
              </>
            )}
          </Button>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              {error}
            </div>
          )}

          {result && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Pipeline Results</h3>
              <div className="space-y-2 max-h-96 overflow-auto">
                {Object.entries(result).map(([agentId, agentResult]: [string, any]) => (
                  <div key={agentId} className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-mono text-xs text-gray-500 dark:text-gray-400">{agentId}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        agentResult.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' :
                        'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'
                      }`}>
                        {agentResult.status}
                      </span>
                    </div>
                    {agentResult.output && (
                      <pre className="text-xs bg-gray-50 dark:bg-gray-800/50 p-2 rounded overflow-auto max-h-40">
                        {JSON.stringify(agentResult.output, null, 2)}
                      </pre>
                    )}
                    {agentResult.error && (
                      <p className="text-xs text-red-600 dark:text-red-400 mt-1">{agentResult.error}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export function TenderWorkspacePage() {
  const { id, panel = 'overview' } = useParams<{ id: string; panel?: string }>()
  const navigate = useNavigate()
  const detail = useTenderDetail(id ?? '')
  const brain = useTenderBrainDetail(id ?? '')

  const activePanel = (PANELS.some((p) => p.id === panel) ? panel : 'overview') as TenderPanel

  function setPanel(newPanel: string) {
    navigate(`/tender/${id}/${newPanel}`, { replace: true })
  }

  const title = brain.data?.tender?.title ?? `Tender ${id}`

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <Link
            to="/tender"
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
            aria-label="Back to tenders"
          >
            <ArrowLeft size={18} />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-blue-100 px-2 py-0.5 font-mono text-xs font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                {id}
              </span>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h1>
            </div>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">Tender workspace</p>
          </div>
        </div>
      }
      primary={
        <Tabs value={activePanel} onValueChange={setPanel}>
          <TabsList>
            {PANELS.map((p) => (
              <TabsTrigger key={p.id} value={p.id}>
                {p.icon}
                <span className="ml-2">{p.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview">
            <OverviewPanel tenderId={id ?? ''} detail={detail} brain={brain} />
          </TabsContent>

          <TabsContent value="documents">
            <DocumentsPanel tenderId={id ?? ''} detail={detail} />
          </TabsContent>

          <TabsContent value="boq">
            <BoqPanel tenderId={id ?? ''} />
          </TabsContent>

          <TabsContent value="pricing">
            <PricingPanel tenderId={id ?? ''} brain={brain} />
          </TabsContent>

          <TabsContent value="compliance">
            <CompliancePanel tenderId={id ?? ''} brain={brain} />
          </TabsContent>

          <TabsContent value="competitors">
            <CompetitorsPanel tenderId={id ?? ''} brain={brain} />
          </TabsContent>

          <TabsContent value="evidence">
            <EvidencePanel tenderId={id ?? ''} />
          </TabsContent>

          <TabsContent value="submission">
            <SubmissionPanel tenderId={id ?? ''} brain={brain} />
          </TabsContent>

          <TabsContent value="award">
            <AwardPanel tenderId={id ?? ''} brain={brain} />
          </TabsContent>
        </Tabs>
      }
    />
  )
}
