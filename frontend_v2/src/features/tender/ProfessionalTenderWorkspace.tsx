import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity, AlertTriangle, ArrowLeft, BarChart3, BookOpen, Briefcase,
  Check, CheckCircle, Clock, DollarSign, Download, FileText, Info, MessageSquare, Search,
  ExternalLink, Send, Settings, TrendingUp, Users, XCircle,
} from 'lucide-react'
import { approveTenderEstimate, completeTenderBoqRates, downloadTenderArtifact, generateProfitMarginWorkbook, getTenderWorkspace, getUnmatchedBoqSuggestions, openTenderEvidenceDocument, processLiveTender, recheckTenderDataQuality, refreshTenderEstimate, resolveUnmatchedBoqItem, scanTenderChanges, setTenderStageApproval, snapshotEligibilityMatrix, updateTenderWorkspace } from '@entities/tender/api'
import type { TenderWorkspaceData } from '@entities/tender/types'
import { ScreenTemplate } from '@layouts/index'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@shared/ui/Tabs'
import { Skeleton } from '@shared/ui/Skeleton'
import { Button } from '@shared/ui/Button'

type StageId =
  | 'overview' | 'progress' | 'documents' | 'extraction' | 'eligibility'
  | 'document-center' | 'forms' | 'boq' | 'rate-analysis' | 'pricing'
  | 'compliance' | 'validation' | 'risks' | 'team' | 'submission' | 'outputs'

const STAGES: Array<{ id: StageId; label: string; icon: React.ElementType }> = [
  { id: 'overview', label: '1 Overview', icon: Briefcase },
  { id: 'progress', label: '2 Progress', icon: Activity },
  { id: 'documents', label: '3 Explorer', icon: Search },
  { id: 'extraction', label: '4 Extraction', icon: TrendingUp },
  { id: 'eligibility', label: '5 Eligibility', icon: BookOpen },
  { id: 'document-center', label: '6 Documents', icon: FileText },
  { id: 'forms', label: '7 Forms', icon: FileText },
  { id: 'boq', label: '8 BOQ', icon: BarChart3 },
  { id: 'rate-analysis', label: '9 Rates', icon: DollarSign },
  { id: 'pricing', label: '10 Pricing', icon: DollarSign },
  { id: 'compliance', label: '11 PPR', icon: Info },
  { id: 'validation', label: '12 Validation', icon: CheckCircle },
  { id: 'risks', label: '13 Risks', icon: AlertTriangle },
  { id: 'team', label: '14 Team', icon: Users },
  { id: 'submission', label: '15 Submission', icon: Send },
  { id: 'outputs', label: '16 Outputs', icon: Download },
]

const WORKFLOW = [
  'Review Tender', 'Verify Eligibility', 'Collect Documents', 'Prepare Forms',
  'Analyze & Price BOQ', 'Validate Compliance', 'Internal Approval', 'Final Submission',
]

function money(value: unknown) {
  const number = Number(value || 0)
  if (!number) return 'Not available'
  return `৳${(number / 1e7).toLocaleString(undefined, { maximumFractionDigits: 2 })}Cr`
}

function countdown(seconds: number | null) {
  if (seconds == null) return 'Deadline unavailable'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  return `${days}d ${hours}h`
}

function tone(value: number) {
  return value >= 80 ? 'text-green-600' : value >= 50 ? 'text-amber-600' : 'text-red-600'
}

function Card({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-200">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

function Metric({ label, value, critical = false }: { label: string; value: React.ReactNode; critical?: boolean }) {
  return (
    <div className="min-w-[130px] rounded-lg border border-gray-200 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-900">
      <p className="text-[10px] uppercase tracking-wide text-gray-500">{label}</p>
      <p className={`mt-0.5 text-sm font-semibold ${critical ? 'text-red-600' : 'text-gray-900 dark:text-white'}`}>{value}</p>
    </div>
  )
}

function Status({ ok, pending = 'Pending' }: { ok: boolean; pending?: string }) {
  return ok
    ? <span className="inline-flex items-center gap-1 text-xs font-medium text-green-600"><CheckCircle size={14} /> Complete</span>
    : <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600"><Clock size={14} /> {pending}</span>
}

function EnterpriseStrip({ data }: { data: TenderWorkspaceData }) {
  const e = data.enterprise
  return (
    <div className="flex gap-2 overflow-x-auto pb-2" aria-label="Persistent tender metrics">
      <Metric label="Countdown" value={countdown(e.countdown_seconds)} critical={e.countdown_seconds != null && e.countdown_seconds < 86400} />
      <Metric label="Readiness" value={`${e.readiness_score}%`} />
      <Metric label="Compliance" value={`${e.compliance_score}%`} />
      <Metric label="AI confidence" value={e.ai_confidence} />
      <Metric label="Critical alerts" value={e.critical_alerts} critical={e.critical_alerts > 0} />
      <Metric label="Missing documents" value={e.missing_documents} critical={e.missing_documents > 0} />
      <Metric label="BOQ completion" value={`${e.boq_completion}%`} />
      <Metric label="Validation" value={String(e.validation_status).replace('_', ' ')} />
      <Metric label="Estimated profit" value={money(e.estimated_profit)} />
      <Metric label="Win probability" value={e.win_probability == null ? 'Pending' : `${e.win_probability}%`} />
      <Metric label="Assigned owner" value={e.owner} />
      <Metric label="Last updated" value={new Date(e.last_updated).toLocaleString()} />
    </div>
  )
}

function Overview({ d }: { d: TenderWorkspaceData }) {
  const o = d.overview
  const queryClient = useQueryClient()
  const refreshEstimate = useMutation({
    mutationFn: () => refreshTenderEstimate(d.tender_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tender-workspace', d.tender_id] }),
  })
  const approveEstimate = useMutation({
    mutationFn: (candidate: Record<string, any>) => approveTenderEstimate(d.tender_id, candidate),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tender-workspace', d.tender_id] }),
  })
  const items = [
    ['Tender ID', d.tender_id], ['Package', o.package_no], ['Procuring entity', o.procuring_entity],
    ['Agency', o.agency], ['Method', o.method], ['Estimated cost', money(o.estimated_cost_bdt)],
    ['Estimate source', o.estimate_source ? `${String(o.estimate_source).replaceAll('_', ' ')} (${Math.round(Number(o.estimate_confidence || 0) * 100)}%)` : 'Not resolved'],
    ['Tender security', o.tender_security_text || money(o.tender_security_amount_bdt)],
    ['Security evidence', o.requirements_evidence?.document_type ? `${o.requirements_evidence.document_type} · ${o.requirements_evidence.source_entry_type}` : 'Not acquired'],
    ['Submission', o.closing_at ? new Date(o.closing_at).toLocaleString() : 'Not available'],
  ]
  return (
    <div className="space-y-4">
      <Card title="Tender Summary">
        <h3 className="mb-3 text-base font-semibold text-gray-900 dark:text-white">{o.title}</h3>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {items.map(([label, value]) => <Metric key={label} label={label} value={value || 'Not available'} />)}
        </div>
      </Card>
      <Card title="AI Executive Summary">
        <p className="text-sm leading-6 text-gray-700 dark:text-gray-300">{o.ai_summary}</p>
      </Card>
      <Card title="APP Estimate Recovery" action={<Button size="sm" variant="secondary" onClick={() => refreshEstimate.mutate()} disabled={refreshEstimate.isPending}>{refreshEstimate.isPending ? 'Searching APP…' : 'Refresh candidates'}</Button>}>
        {o.estimate_status === 'resolved' && Number(o.estimated_cost_bdt) > 0
          ? <p className="rounded-lg bg-green-50 p-3 text-sm text-green-800">Approved estimate: {money(o.estimated_cost_bdt)} · {String(o.estimate_source).replaceAll('_', ' ')} · {Math.round(Number(o.estimate_confidence || 0) * 100)}% confidence</p>
          : <p className="mb-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">No exact package match was found. Review the ranked PG17 APP candidates before using an estimate in pricing or qualification.</p>}
        <div className="space-y-2">{(o.estimate_candidates ?? []).map((candidate: any, index: number) => <div key={`${candidate.source_record_id}-${index}`} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
          <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1"><p className="text-sm font-semibold">#{index + 1} · {candidate.package_no || 'Package unavailable'} · {money(candidate.amount_bdt)}</p><p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{candidate.title || 'APP title unavailable'}</p><p className="mt-1 text-[11px] text-gray-500">{candidate.pe_office || 'PE unavailable'} · FY {candidate.financial_year || '—'} · confidence {Math.round(Number(candidate.confidence || 0) * 100)}%</p>{candidate.match_evidence && <p className="mt-1 text-[10px] text-gray-500">Title/package {Math.round(Number(candidate.match_evidence.package_or_title_similarity || 0) * 100)}% · PE {Math.round(Number(candidate.match_evidence.pe_office_similarity || 0) * 100)}% · agency {candidate.match_evidence.agency_match ? 'matched' : 'different'}</p>}</div><Button size="sm" disabled={approveEstimate.isPending || Number(candidate.amount_bdt) <= 0} onClick={() => approveEstimate.mutate(candidate)}>Approve estimate</Button></div>
        </div>)}</div>
        {!o.estimate_candidates?.length && o.estimate_status !== 'resolved' && <p className="text-sm text-gray-500">No recovery candidates yet. Refresh to search Works APP records and the live APP source.</p>}
        {approveEstimate.error && <p className="mt-2 text-xs text-red-600">{approveEstimate.error.message}</p>}
      </Card>
    </div>
  )
}

function Progress({ d }: { d: TenderWorkspaceData }) {
  const p = d.progress
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Card title="Overall completion"><p className={`text-3xl font-bold ${tone(p.completion_pct)}`}>{p.completion_pct}%</p></Card>
        <Card title="Submission readiness"><p className={`text-3xl font-bold ${tone(p.readiness_score)}`}>{p.readiness_score}/100</p></Card>
        <Card title="Countdown"><p className="text-3xl font-bold text-gray-900 dark:text-white">{countdown(p.countdown_seconds)}</p></Card>
      </div>
      <Card title="Preparation workflow">
        <div className="grid gap-2 md:grid-cols-4">
          {WORKFLOW.map((name, i) => <div key={name} className="rounded-lg bg-gray-50 p-3 text-xs dark:bg-gray-800"><span className="font-semibold">{i + 1}.</span> {name}</div>)}
        </div>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Missing tasks"><List items={p.missing_tasks} /></Card>
        <Card title="Critical blockers"><List items={p.critical_blockers} danger /></Card>
      </div>
      <Card title="AI next action"><p className="text-sm font-medium text-blue-700 dark:text-blue-300">{p.next_action}</p></Card>
    </div>
  )
}

function List({ items, danger = false }: { items: string[]; danger?: boolean }) {
  return items.length ? (
    <ul className="space-y-2">{items.map(item => <li key={item} className={`flex gap-2 text-sm ${danger ? 'text-red-600' : 'text-gray-700 dark:text-gray-300'}`}><AlertTriangle size={15} className="mt-0.5 shrink-0" />{item}</li>)}</ul>
  ) : <p className="text-sm text-green-600">None</p>
}

function Documents({ d }: { d: TenderWorkspaceData }) {
  const watcher = useMutation({ mutationFn: () => scanTenderChanges(d.tender_id) })
  const required = ['notice', 'tds', 'pcc', 'gcc', 'specifications', 'drawings', 'boq', 'addendum', 'clarification']
  return (
    <Card title="Tender Document Explorer" action={<div className="flex gap-2"><Button size="sm" variant="secondary" onClick={() => watcher.mutate()}>{watcher.isPending ? 'Scanning…' : 'Check deadline & addenda'}</Button><Button size="sm" variant="secondary">Compare selected</Button></div>}>
      {watcher.data && <p className={`mb-3 rounded-lg p-2 text-xs ${watcher.data.changes.length ? 'bg-amber-50 text-amber-800' : 'bg-green-50 text-green-700'}`}>{watcher.data.status}: {watcher.data.changes.length} change(s) · checked {new Date(watcher.data.scanned_at).toLocaleString()}</p>}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {required.map(type => {
          const doc = d.documents.find(item => item.type.includes(type))
          return <div key={type} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <div className="flex items-center justify-between"><span className="text-sm font-medium capitalize">{type}</span><Status ok={Boolean(doc)} pending="Missing" /></div>
            <p className="mt-2 truncate text-xs text-gray-500">{doc?.name || 'Upload or acquire from e-GP'}</p>
          </div>
        })}
      </div>
    </Card>
  )
}

function HighlightedClause({ text, highlight }: { text: string; highlight: string }) {
  const index = text.toLowerCase().indexOf(highlight.toLowerCase())
  if (index < 0 || !highlight) return <>{text}</>
  return <>{text.slice(0, index)}<mark className="rounded bg-yellow-200 px-0.5 text-gray-950">{text.slice(index, index + highlight.length)}</mark>{text.slice(index + highlight.length)}</>
}

function Extraction({ d }: { d: TenderWorkspaceData }) {
  const [selected, setSelected] = useState<TenderWorkspaceData['requirements'][number] | null>(null)
  const [viewerError, setViewerError] = useState<string | null>(null)
  const openSource = async () => {
    if (!selected?.evidence.document_url) return
    setViewerError(null)
    try {
      await openTenderEvidenceDocument(selected.evidence.document_url, selected.evidence.page_number)
    } catch (error) {
      setViewerError(error instanceof Error ? error.message : 'Could not open evidence document')
    }
  }
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <Card title="AI Requirement Extraction">
        {d.requirements.length ? <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-xs uppercase text-gray-500"><th className="p-2">Requirement</th><th className="p-2">Extracted value</th><th className="p-2">Evidence</th></tr></thead><tbody>{d.requirements.map(r => <tr key={r.key} className={`border-t border-gray-100 dark:border-gray-800 ${selected?.key === r.key ? 'bg-blue-50 dark:bg-blue-950/20' : ''}`}><td className="p-2 font-medium">{r.label}</td><td className="p-2">{String(r.value)}</td><td className="p-2"><button onClick={() => setSelected(r)} className="inline-flex items-center gap-1 font-medium text-blue-600 hover:underline"><Search size={13} />{r.evidence.page_number ? `TDS page ${r.evidence.page_number}` : 'View evidence'}</button></td></tr>)}</tbody></table></div> : <p className="text-sm text-amber-600">Acquire the TDS and run the specification-intelligence agent.</p>}
      </Card>
      <Card title="Document Evidence Viewer">
        {selected ? <div className="space-y-3">
          <div><p className="text-xs uppercase tracking-wide text-gray-500">{selected.label}</p><p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">{String(selected.value)}</p></div>
          <div className="grid grid-cols-2 gap-2 text-xs"><div className="rounded bg-gray-50 p-2 dark:bg-gray-800"><span className="block text-gray-500">Document</span>{selected.evidence.document_type}</div><div className="rounded bg-gray-50 p-2 dark:bg-gray-800"><span className="block text-gray-500">Page</span>{selected.evidence.page_number ?? 'Structured record'}</div></div>
          {selected.evidence.clause_text ? <blockquote className="max-h-72 overflow-auto rounded-lg border-l-4 border-blue-500 bg-blue-50 p-3 text-sm leading-6 text-gray-800 dark:bg-blue-950/30 dark:text-gray-200"><HighlightedClause text={selected.evidence.clause_text} highlight={selected.evidence.highlight_text} /></blockquote> : <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">The criterion is stored in structured TDS knowledge, but the exact PDF text location was not found.</p>}
          <p className="text-[10px] text-gray-500">Evidence ID: {selected.evidence.knowledge_entry_id || 'pending'} · {selected.evidence.match_method}</p>
          <Button onClick={openSource} disabled={!selected.evidence.document_url} leftIcon={<ExternalLink size={14} />}>Open full source document{selected.evidence.page_number ? ` · page ${selected.evidence.page_number}` : ''}</Button>
          {viewerError && <p className="text-xs text-red-600">{viewerError}</p>}
        </div> : <p className="text-sm text-gray-500">Select any extracted criterion to see its exact TDS page, supporting clause and stored knowledge reference.</p>}
      </Card>
    </div>
  )
}

function Eligibility({ d }: { d: TenderWorkspaceData }) {
  const snapshot = useMutation({ mutationFn: () => snapshotEligibilityMatrix(d.tender_id) })
  const matrix = d.eligibility.matrix ?? []
  return (
    <div className="space-y-4">
      <Card title="Eligibility result"><p className={`text-2xl font-bold ${tone(d.eligibility.score)}`}>{d.eligibility.score.toFixed(0)}% · {d.eligibility.recommendation}</p><p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{d.eligibility.explanation}</p></Card>
      <Card title="Eligibility Evidence Matrix" action={<Button size="sm" variant="secondary" onClick={() => snapshot.mutate()}>{snapshot.isPending ? 'Saving…' : 'Save evidence snapshot'}</Button>}>
        <p className="mb-3 text-xs text-gray-500">Company dossier {d.eligibility.contractor_id || 'not selected'} · {d.eligibility.company_documents_considered || 0} PG17 documents considered. “Evidence found” still requires numeric verification before it becomes a pass.</p>
        {matrix.length ? <div className="overflow-auto"><table className="w-full min-w-[1050px] text-xs"><thead><tr className="text-left text-gray-500"><th className="p-2">Criterion</th><th className="p-2">Required</th><th className="p-2">Company value</th><th className="p-2">Company evidence</th><th className="p-2">Expiry</th><th className="p-2">Result</th><th className="p-2">Tender evidence</th></tr></thead><tbody>{matrix.map((row: any) => <tr key={row.criterion} className="border-t border-gray-100 dark:border-gray-800"><td className="p-2 font-medium">{row.criterion}</td><td className="p-2">{String(row.required_value)}</td><td className="p-2">{row.contractor_value == null ? 'Not extracted' : String(row.contractor_value)}</td><td className="p-2">{row.company_evidence?.length ? <details><summary className="cursor-pointer text-blue-600">{row.company_evidence.length} document(s)</summary><div className="mt-1 space-y-1">{row.company_evidence.map((doc: any) => <p key={doc.document_id} className="max-w-xs truncate" title={doc.filename}>{doc.filename}</p>)}</div></details> : 'Missing'}</td><td className={`p-2 ${row.expiry_status === 'possibly_expired' ? 'font-semibold text-red-600' : ''}`}>{String(row.expiry_status).replaceAll('_', ' ')}</td><td className="p-2 font-semibold uppercase">{String(row.status).replaceAll('_', ' ')}</td><td className="p-2">{row.tender_evidence?.page_number ? `TDS p.${row.tender_evidence.page_number}` : row.tender_evidence?.match_method}</td></tr>)}</tbody></table></div> : <p className="text-sm text-gray-500">Acquire and extract the TDS to build the evidence matrix.</p>}
        {snapshot.isSuccess && <p className="mt-2 text-xs text-green-700">Evidence matrix persisted to the knowledge database.</p>}
      </Card>
      <Card title="Pass / fail checks"><div className="grid gap-2 md:grid-cols-2">{d.eligibility.checks.map(c => <div key={c.name} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700"><div className="flex justify-between"><span className="text-sm font-medium">{c.name}</span><Status ok={c.status === 'pass'} /></div><p className="mt-1 text-xs text-gray-500">{c.explanation}</p></div>)}</div></Card>
    </div>
  )
}

function DocumentCenter({ d, save }: { d: TenderWorkspaceData; save: (update: any) => void }) {
  const statuses = Object.fromEntries(d.document_checklist.map(item => [item.name, item.status]))
  return (
    <Card title="Document Preparation Center">
      <div className="grid gap-2 lg:grid-cols-2">
        {d.document_checklist.map(item => <button key={item.name} onClick={() => save({ document_statuses: { ...statuses, [item.name]: item.status === 'verified' ? 'missing' : 'verified' } })} className="flex items-center justify-between rounded-lg border border-gray-200 p-3 text-left dark:border-gray-700"><span><span className="block text-sm font-medium">{item.name}</span><span className="text-xs text-gray-500">{item.required ? 'Mandatory' : 'When applicable'}</span></span><Status ok={item.status === 'verified' || item.status === 'uploaded'} pending={item.status} /></button>)}
      </div>
    </Card>
  )
}

function Forms({ d, save }: { d: TenderWorkspaceData; save: (update: any) => void }) {
  const statuses = Object.fromEntries(d.forms.map(form => [form.name, form.status]))
  return <Card title="Form Auto-Fill"><div className="grid gap-2 md:grid-cols-2">{d.forms.map(form => <button key={form.name} onClick={() => save({ form_statuses: { ...statuses, [form.name]: form.status === 'ready' ? 'missing_fields' : 'ready' } })} className="flex items-center justify-between rounded-lg border border-gray-200 p-3 text-left dark:border-gray-700"><span className="text-sm">{form.name}</span><Status ok={form.status === 'ready'} pending="Missing fields" /></button>)}</div><p className="mt-4 text-xs text-gray-500">Mark each generated and reviewed form ready; submission readiness recalculates immediately.</p></Card>
}

function Boq({ d, id }: { d: TenderWorkspaceData; id: string }) {
  const queryClient = useQueryClient()
  const [zone, setZone] = useState('A')
  const [search, setSearch] = useState('')
  const suggestions = useQuery({ queryKey: ['boq-unmatched', id], queryFn: () => getUnmatchedBoqSuggestions(id), enabled: Boolean(d.boq.unmatched_items) })
  const resolveItem = useMutation({
    mutationFn: (input: { item_id: string; sor_code: string; agency: string; zone: string }) => resolveUnmatchedBoqItem(id, input),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['tender-workspace', id] }); queryClient.invalidateQueries({ queryKey: ['boq-unmatched', id] }) },
  })
  const completion = useMutation({
    mutationFn: () => completeTenderBoqRates(id, { sor_agency: 'BWDB', zone }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tender-workspace', id] }),
  })
  const items = (d.boq.items ?? []).filter((item: any) => `${item.code} ${item.description}`.toLowerCase().includes(search.toLowerCase()))
  return <div className="space-y-4">
    <Card title="BOQ Rate Completion" action={<div className="flex gap-2"><Link to={`/tender/${id}/pricing-lab`}><Button size="sm" variant="secondary">Pricing laboratory</Button></Link>{d.boq.export_url && <Button size="sm" variant="secondary" onClick={() => downloadTenderArtifact(d.boq.export_url, `BOQ_Rate_Completion_${id}.xlsx`)} leftIcon={<Download size={14} />}>Export Excel</Button>}</div>}>
      <div className="flex flex-wrap items-end gap-3">
        <div><p className="mb-1 text-[10px] uppercase text-gray-500">SOR agencies</p><div className="flex gap-1">{['BWDB', 'LGED', 'PWD'].map(agency => <span key={agency} className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700">{agency}</span>)}</div></div>
        <label className="text-xs text-gray-500">Zone<select value={zone} onChange={event => setZone(event.target.value)} className="ml-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900">{['A', 'B', 'C', 'D'].map(value => <option key={value}>{value}</option>)}</select></label>
        <Button onClick={() => completion.mutate()} disabled={completion.isPending}>{completion.isPending ? 'Extracting & matching…' : 'Complete rates from SOR'}</Button>
      </div>
      {completion.error && <p className="mt-2 text-xs text-red-600">{completion.error.message}</p>}
      <div className="mt-4 grid gap-3 sm:grid-cols-5"><Metric label="Items" value={d.boq.total_items || 0} /><Metric label="Matched" value={d.boq.matched_items || 0} /><Metric label="Unmatched" value={d.boq.unmatched_items || 0} critical={Boolean(d.boq.unmatched_items)} /><Metric label="Completed total" value={money(d.boq.completed_total_bdt)} /><Metric label="Variances" value={d.boq.variances || 0} critical={Boolean(d.boq.variances)} /></div>
    </Card>
    {Boolean(d.boq.unmatched_items) && <Card title="Unmatched Item Resolution">
      <div className="space-y-3">{(suggestions.data?.items ?? []).map((item: any) => <div key={item.id} className="rounded-lg border border-amber-200 p-3"><p className="text-sm font-medium">{item.item_no} · {item.description}</p><div className="mt-2 flex flex-wrap gap-2">{item.candidates.map((candidate: any) => <Button key={candidate.id} size="sm" variant="secondary" onClick={() => resolveItem.mutate({ item_id: item.id, sor_code: candidate.code, agency: candidate.agency, zone })}>{candidate.agency} {candidate.code} · {money(candidate[`zone_${zone.toLowerCase()}`])}</Button>)}</div>{!item.candidates.length && <p className="mt-2 text-xs text-red-600">No strong SOR suggestion; manual rate evidence is required.</p>}</div>)}</div>
      {suggestions.isLoading && <p className="text-sm text-gray-500">Finding BWDB/LGED/PWD candidates…</p>}
    </Card>}
    <Card title="Completed BOQ Items" action={<input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search item or code" className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs dark:border-gray-700 dark:bg-gray-900" />}>
      {items.length ? <div className="max-h-[620px] overflow-auto"><table className="min-w-[1100px] w-full text-xs"><thead className="sticky top-0 bg-gray-50 text-left text-gray-500 dark:bg-gray-800"><tr>{['Item', 'Code', 'Description', 'Unit', 'Qty', 'Agency', 'SOR rate', 'Completed rate', 'Amount', 'Status'].map(label => <th key={label} className="p-2">{label}</th>)}</tr></thead><tbody>{items.map((item: any, index: number) => <tr key={`${item.item_no}-${item.code}-${index}`} className="border-t border-gray-100 dark:border-gray-800"><td className="p-2">{item.item_no || index + 1}</td><td className="p-2 font-mono">{item.code || '—'}</td><td className="max-w-md p-2">{item.description}</td><td className="p-2">{item.unit}</td><td className="p-2 text-right">{item.quantity}</td><td className="p-2">{item.agency || '—'}</td><td className="p-2 text-right">{item.sor_rate?.toLocaleString() ?? '—'}</td><td className="p-2 text-right font-medium">{item.completed_rate?.toLocaleString() ?? '—'}</td><td className="p-2 text-right">{item.completed_amount?.toLocaleString() ?? '—'}</td><td className="p-2"><span className={`rounded px-2 py-1 text-[10px] ${item.sor_rate != null ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{item.sor_rate != null ? item.match_type || 'matched' : item.unmatched_reason || 'unmatched'}</span></td></tr>)}</tbody></table></div> : <p className="text-sm text-gray-500">Run BOQ rate completion to extract items, match BWDB/LGED/PWD rates, calculate totals and identify unmatched work.</p>}
    </Card>
  </div>
}

function RateAnalysis({ d }: { d: TenderWorkspaceData }) {
  return <Card title="Rate Analysis"><div className="grid gap-3 sm:grid-cols-3"><Metric label="SOR rates connected" value={Number(d.rate_analysis.sor_rates_available || 0).toLocaleString()} /><Metric label="Previous awards" value={Number(d.rate_analysis.previous_awards_available || 0).toLocaleString()} /><Metric label="Analysis status" value={String(d.rate_analysis.status).replace('_', ' ')} /></div><p className="mt-4 text-sm text-gray-500">Each BOQ item can combine estimated cost, SOR, market, previous award, recommended rate, margin and risk.</p></Card>
}

function Pricing({ d, id }: { d: TenderWorkspaceData; id: string }) {
  const [values, setValues] = useState({ direct_cost_bdt: Number(d.pricing.direct_cost || d.overview.estimated_cost_bdt || 0), overhead_pct: 5, tax_vat_pct: 7.5, contingency_pct: 2, target_profit_pct: 10 })
  const calculator = useMutation({
    mutationFn: () => generateProfitMarginWorkbook(id, values),
    onSuccess: (result) => downloadTenderArtifact(result.artifact.download_url, result.artifact.name),
  })
  return <div className="space-y-4"><Card title="Pricing Strategy" action={<Link to={`/tender/${id}/pricing-lab`}><Button size="sm">Compare scenarios</Button></Link>}><div className="grid gap-3 sm:grid-cols-4"><Metric label="Total bid" value={money(d.pricing.total_bid_value)} /><Metric label="Direct cost" value={money(d.pricing.direct_cost)} /><Metric label="Discount" value={`${Number(d.pricing.discount_pct || 0).toFixed(2)}%`} /><Metric label="Win probability" value={d.pricing.win_probability == null ? 'Pending' : `${d.pricing.win_probability}%`} /></div><div className="mt-4 grid grid-cols-3 gap-2">{d.pricing.scenarios.map((s: string) => <div key={s} className="rounded-lg border border-gray-200 p-3 text-center text-sm font-medium dark:border-gray-700">{s}</div>)}</div></Card>
    <Card title="Profit Margin Calculator · Excel Output">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {([
          ['direct_cost_bdt', 'Direct cost BDT'], ['overhead_pct', 'Overhead %'],
          ['contingency_pct', 'Contingency %'], ['target_profit_pct', 'Target profit %'],
          ['tax_vat_pct', 'Tax / VAT %'],
        ] as const).map(([key, label]) => <label key={key} className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}<input type="number" min="0" step="0.01" value={values[key]} onChange={event => setValues(current => ({ ...current, [key]: Number(event.target.value) }))} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" /></label>)}
      </div>
      <Button className="mt-4" disabled={!values.direct_cost_bdt || calculator.isPending} onClick={() => calculator.mutate()} leftIcon={<Download size={14} />}>{calculator.isPending ? 'Generating workbook…' : 'Calculate & Download Excel'}</Button>
      {calculator.data && <p className="mt-3 text-sm text-green-700">Recommended bid {money(calculator.data.recommended_bid_bdt)} · Profit {money(calculator.data.profit_bdt)} · Effective margin {calculator.data.effective_margin_pct.toFixed(2)}%</p>}
      {calculator.error && <p className="mt-3 text-sm text-red-600">{calculator.error.message}</p>}
    </Card>
  </div>
}

function Compliance({ d }: { d: TenderWorkspaceData }) {
  return <div className="space-y-4"><Card title="PPR Compliance Center"><p className={`text-3xl font-bold ${tone(d.compliance.score)}`}>{d.compliance.score}%</p><p className="text-sm text-gray-500">{d.compliance.requirements_linked} requirements linked to evidence</p></Card><Card title="Violations and mandatory actions"><List items={d.compliance.violations} danger /></Card></div>
}

function Validation({ d, id }: { d: TenderWorkspaceData; id: string }) {
  const queryClient = useQueryClient()
  const recheck = useMutation({
    mutationFn: () => recheckTenderDataQuality(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tender-workspace', id] }),
  })
  const quality = d.data_quality
  return <div className="space-y-4">
    <Card title="Pre-agent Data Quality Guardrails" action={<Button size="sm" variant="secondary" onClick={() => recheck.mutate()} disabled={recheck.isPending}>{recheck.isPending ? 'Checking…' : 'Recheck data'}</Button>}>
      <div className="grid gap-3 sm:grid-cols-4"><Metric label="Quality score" value={`${quality.score}/100`} /><Metric label="Gate" value={quality.status.replace('_', ' ')} critical={quality.status === 'blocked'} /><Metric label="Critical" value={quality.critical_count} critical={quality.critical_count > 0} /><Metric label="Warnings" value={quality.warning_count} critical={quality.warning_count > 0} /></div>
      <p className={`mt-3 rounded-lg p-2 text-xs ${quality.agent_use_allowed ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>{quality.agent_use_allowed ? 'Downstream agents may use these tender inputs.' : 'Downstream agents are blocked until critical findings are resolved.'}</p>
      <div className="mt-3 space-y-2">{quality.issues.map((issue, index) => <div key={`${issue.code}-${index}`} className={`rounded-lg border p-3 ${issue.severity === 'critical' ? 'border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/20' : 'border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/20'}`}><div className="flex justify-between gap-2"><p className="text-sm font-medium">{issue.message}</p><span className="text-[10px] font-semibold uppercase">{issue.severity}</span></div><p className="mt-1 font-mono text-[10px] text-gray-500">{issue.code}</p><details className="mt-2"><summary className="cursor-pointer text-xs text-blue-600">Evidence</summary><pre className="mt-1 max-h-48 overflow-auto rounded bg-gray-950 p-2 text-[10px] text-emerald-300">{JSON.stringify(issue.evidence, null, 2)}</pre></details></div>)}</div>
      {!quality.issues.length && <p className="mt-3 text-sm text-green-700">No duplicate, placeholder, deadline, currency, or stale APP issues detected.</p>}
    </Card>
    <Card title="Pre-submission Validation Center"><div className="grid gap-2 md:grid-cols-2">{d.validation.map(check => <div key={check.name} className="flex items-center justify-between rounded-lg border border-gray-200 p-3 dark:border-gray-700"><span className="text-sm">{check.name}</span>{check.passed ? <Check className="text-green-600" size={18} /> : <XCircle className="text-red-600" size={18} />}</div>)}</div></Card>
  </div>
}

function Risks({ d }: { d: TenderWorkspaceData }) {
  return <Card title="Risk Dashboard"><div className="space-y-3">{d.risks.map(r => <div key={r.category} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700"><div className="flex items-center justify-between"><span className="font-medium">{r.category}</span><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${r.level === 'high' ? 'bg-red-100 text-red-700' : r.level === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>{r.level}</span></div><p className="mt-1 text-sm">{r.issue}</p><p className="mt-1 text-xs text-blue-600">AI mitigation: {r.mitigation}</p></div>)}</div></Card>
}

function Team({ d, save, id }: { d: TenderWorkspaceData; save: (update: any) => void; id: string }) {
  const queryClient = useQueryClient()
  const approval = useMutation({
    mutationFn: ({ stage, status }: { stage: string; status: 'approved' | 'revoked' }) => setTenderStageApproval(id, stage, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tender-workspace', id] }),
  })
  return <div className="space-y-4"><Card title="Team Tasks"><div className="space-y-2">{d.collaboration.tasks.map(task => <button key={task.id} onClick={() => save({ tasks: d.collaboration.tasks.map(t => t.id === task.id ? { ...t, status: t.status === 'done' ? 'todo' : 'done' } : t) })} className="flex w-full items-center justify-between rounded-lg border border-gray-200 p-3 text-left dark:border-gray-700"><span><span className="block text-sm font-medium">{task.title}</span><span className="text-xs text-gray-500">{task.owner} · {task.stage}</span></span><Status ok={task.status === 'done'} pending={task.status} /></button>)}</div></Card><Card title="Bid Approval Command Center"><div className="grid gap-2 md:grid-cols-2">{(d.collaboration.approval_stages ?? []).map((item: any) => <div key={item.stage} className="flex items-center justify-between rounded-lg border border-gray-200 p-3 dark:border-gray-700"><div><p className="text-sm font-medium capitalize">{item.stage}</p><p className="text-xs text-gray-500">{item.status}</p></div><Button size="sm" variant={item.status === 'approved' ? 'secondary' : 'primary'} onClick={() => approval.mutate({ stage: item.stage, status: item.status === 'approved' ? 'revoked' : 'approved' })}>{item.status === 'approved' ? 'Revoke' : 'Approve'}</Button></div>)}</div><div className="mt-3 flex items-center gap-2 text-sm text-gray-500"><MessageSquare size={16} /> {d.collaboration.comments.length} comments · {d.collaboration.approvals.length}/6 stage approvals · {d.collaboration.activity.length} activity events</div></Card></div>
}

function Submission({ d, id }: { d: TenderWorkspaceData; id: string }) {
  const components = Object.entries(d.submission.readiness_components || {}) as Array<[string, { score: number; weight: number }]>
  return <div className="space-y-4"><Card title="Final Submission Center" action={<a href={`/api/tender/${id}/bundle`}><Button size="sm">Export ZIP package</Button></a>}><p className={`text-4xl font-bold ${tone(d.submission.readiness_score)}`}>{d.submission.readiness_score}/100</p><p className="mt-1 text-xs text-gray-500">Automatically recalculated {d.submission.recalculated_at ? new Date(d.submission.recalculated_at).toLocaleString() : 'now'}</p><div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{components.map(([name, component]) => <div key={name} className="rounded-lg border border-gray-200 p-2 dark:border-gray-700"><div className="flex justify-between text-xs"><span className="capitalize">{name}</span><span>{component.score}%</span></div><div className="mt-1 h-1.5 rounded bg-gray-100 dark:bg-gray-800"><div className="h-full rounded bg-blue-500" style={{ width: `${component.score}%` }} /></div><p className="mt-1 text-[10px] text-gray-500">{component.weight}% weight</p></div>)}</div><div className="mt-4 grid gap-2 md:grid-cols-2">{d.submission.files.map((f: any) => <div key={f.name} className="flex justify-between rounded-lg border border-gray-200 p-2 text-sm dark:border-gray-700"><span>{f.name}</span><span>{f.status}</span></div>)}</div></Card><Card title="Submission sequence"><ol className="space-y-2">{d.submission.sequence.map((step: string, i: number) => <li key={step} className="text-sm"><span className="mr-2 font-semibold">{i + 1}.</span>{step}</li>)}</ol></Card><Card title="Post-submission checklist"><List items={d.submission.post_submission} /></Card></div>
}

function Outputs({ d }: { d: TenderWorkspaceData }) {
  return (
    <div className="space-y-4">
      <Card title="Persisted Runtime Output">
        <p className="text-sm text-gray-600 dark:text-gray-400">{d.outputs.runtime_summary || 'Run acquisition to persist a complete runtime snapshot.'}</p>
        {Object.keys(d.outputs.pipeline_result || {}).length > 0 && (
          <details className="mt-3">
            <summary className="cursor-pointer text-sm font-medium text-blue-600">View pipeline JSON</summary>
            <pre className="mt-2 max-h-96 overflow-auto rounded-lg bg-gray-950 p-3 text-xs text-emerald-300">{JSON.stringify(d.outputs.pipeline_result, null, 2)}</pre>
          </details>
        )}
      </Card>
      <Card title="Downloadable Files">
        {d.outputs.artifacts.length ? <div className="space-y-2">{d.outputs.artifacts.map(artifact => (
          <div key={`${artifact.sha256}-${artifact.name}`} className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <div className="min-w-0"><p className="truncate text-sm font-medium">{artifact.name}</p><p className="text-xs text-gray-500">{artifact.kind} · {(artifact.size_bytes / 1024).toFixed(1)} KB · SHA-256 {artifact.sha256.slice(0, 12)}…</p></div>
            <Button size="sm" variant="secondary" onClick={() => downloadTenderArtifact(artifact.download_url, artifact.name)} leftIcon={<Download size={14} />}>Download</Button>
          </div>
        ))}</div> : <p className="text-sm text-gray-500">No generated files have been persisted for this tender yet.</p>}
      </Card>
      <Card title="Agent Outputs">
        <div className="space-y-2">{d.agent_runs.map(run => (
          <details key={run.run_id} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <summary className="cursor-pointer text-sm font-medium">{run.agent_name} · <span className={run.status === 'success' ? 'text-green-600' : 'text-red-600'}>{run.status}</span></summary>
            <pre className="mt-2 max-h-80 overflow-auto rounded bg-gray-950 p-3 text-xs text-emerald-300">{JSON.stringify(run.output || { error: run.error }, null, 2)}</pre>
            <Link className="mt-2 inline-block text-xs text-blue-600" to={`/trust/results/${run.run_id}`}>Open full persisted result</Link>
          </details>
        ))}</div>
      </Card>
    </div>
  )
}

export function ProfessionalTenderWorkspace() {
  const { id = '', panel = 'overview' } = useParams<{ id: string; panel?: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['tender-workspace', id], queryFn: () => getTenderWorkspace(id), enabled: Boolean(id), refetchInterval: 15_000 })
  const mutation = useMutation({
    mutationFn: (update: any) => updateTenderWorkspace(id, update),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tender-workspace', id] }),
  })
  const processMutation = useMutation({
    mutationFn: () => processLiveTender(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tender-workspace', id] }),
  })
  const active = (STAGES.some(stage => stage.id === panel) ? panel : 'overview') as StageId
  const d = query.data
  const content = useMemo(() => {
    if (!d) return null
    const save = (update: any) => mutation.mutate(update)
    const map: Record<StageId, React.ReactNode> = {
      overview: <Overview d={d} />, progress: <Progress d={d} />, documents: <Documents d={d} />,
      extraction: <Extraction d={d} />, eligibility: <Eligibility d={d} />,
      'document-center': <DocumentCenter d={d} save={save} />, forms: <Forms d={d} save={save} />,
      boq: <Boq d={d} id={id} />, 'rate-analysis': <RateAnalysis d={d} />,
      pricing: <Pricing d={d} id={id} />, compliance: <Compliance d={d} />,
      validation: <Validation d={d} id={id} />, risks: <Risks d={d} />, team: <Team d={d} save={save} id={id} />,
      submission: <Submission d={d} id={id} />,
      outputs: <Outputs d={d} />,
    }
    return map[active]
  }, [active, d, id, mutation])

  return (
    <ScreenTemplate
      header={<div className="flex items-start justify-between gap-4"><div className="flex items-start gap-3"><Link to="/tender" className="mt-1 rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"><ArrowLeft size={18} /></Link><div><div className="flex items-center gap-2"><span className="rounded bg-blue-100 px-2 py-0.5 font-mono text-xs text-blue-700">{id}</span><h1 className="text-lg font-semibold text-gray-900 dark:text-white">{d?.overview.title || `Tender ${id}`}</h1></div><p className="mt-0.5 text-sm text-gray-500">Integrated bid preparation workspace · Works procurement</p></div></div><Button onClick={() => processMutation.mutate()} disabled={processMutation.isPending}>{processMutation.isPending ? 'Acquiring & extracting…' : 'Acquire Live Tender & Run Agents'}</Button></div>}
      kpiStrip={d ? <EnterpriseStrip data={d} /> : <Skeleton className="h-16 w-full rounded-xl" />}
      primary={query.isLoading ? <Skeleton className="h-96 w-full rounded-xl" /> : query.error ? <Card title="Workspace unavailable"><p className="text-sm text-red-600">{query.error.message}</p></Card> : (
        <Tabs value={active} onValueChange={value => navigate(`/tender/${id}/${value}`, { replace: true })}>
          <TabsList>{STAGES.map(stage => <TabsTrigger key={stage.id} value={stage.id}><stage.icon size={15} /><span className="ml-1.5">{stage.label}</span></TabsTrigger>)}</TabsList>
          {STAGES.map(stage => <TabsContent key={stage.id} value={stage.id}>{stage.id === active ? content : null}</TabsContent>)}
        </Tabs>
      )}
      aiDock={d ? <div className="space-y-3"><Card title="Bid Control"><div className="space-y-2 text-xs"><p><strong>Next:</strong> {d.progress.next_action}</p><p><strong>Owner:</strong> {d.enterprise.owner}</p><p><strong>Updated:</strong> {new Date(d.enterprise.last_updated).toLocaleString()}</p>{processMutation.isSuccess && <p className="text-green-600"><strong>Pipeline:</strong> acquisition and extraction completed</p>}{processMutation.error && <p className="text-red-600">{processMutation.error.message}</p>}</div></Card><Card title="Agent Results"><div className="space-y-2">{d.agent_runs.length ? d.agent_runs.slice(0, 8).map(run => <Link key={run.run_id} to={`/trust/results/${run.run_id}`} className="flex items-center justify-between gap-2 text-xs hover:text-blue-600"><span className="truncate">{run.agent_name}</span><span className={run.status === 'success' ? 'text-green-600' : run.status === 'failed' ? 'text-red-600' : 'text-amber-600'}>{run.status}</span></Link>) : <p className="text-xs text-gray-500">Run acquisition to see persisted agent outputs.</p>}</div></Card></div> : undefined}
    />
  )
}
