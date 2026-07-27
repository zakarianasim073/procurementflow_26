import { Link, useSearchParams } from 'react-router-dom'
import { AlertTriangle, Radio, Search as SearchIcon, Activity, Play, Loader2, Zap as ZapIcon, CheckCircle, Database, Target, Bell, RefreshCw, Trash2 } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@shared/ui/Tabs'
import { TenderCard } from '@entities/cards/TenderCard'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { useDiscoveryFilters } from './useDiscoveryFilters'
import { FilterBar } from './FilterBar'
import { useExecutivePipeline, useRecentAgentResults, useAgents, useRunAgent } from '@hooks/index'
import { RadarFeed } from '@widgets/opportunity/index'
import { Button } from '@shared/ui/Button'
import { Input } from '@shared/ui/Input'
import { Card } from '@shared/ui/Card'
import { useState } from 'react'
import { fetchJson } from '@entities/sharedApi'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createTenderAlertFilter, deleteTenderAlertFilter, evaluateTenderAlerts, getAgencyLiveTenders, getBidShortlist, getLiveEnrichmentQueue, getTenderAlerts, markTenderAlertRead, refreshLiveEnrichmentQueue, runLiveEnrichmentQueue } from '@entities/executive/api'

interface DiscoveryTab {
  id: string
  label: string
  icon: React.ReactNode
}

const TABS: DiscoveryTab[] = [
  { id: 'search', label: 'Search', icon: <SearchIcon className="h-4 w-4" /> },
  { id: 'live', label: 'Live', icon: <Radio className="h-4 w-4" /> },
  { id: 'enrichment', label: 'Enrichment', icon: <Database className="h-4 w-4" /> },
  { id: 'shortlist', label: 'Bid / No-Bid', icon: <Target className="h-4 w-4" /> },
  { id: 'radar', label: 'Radar', icon: <Activity className="h-4 w-4" /> },
  { id: 'pipeline', label: 'Pipeline', icon: <ZapIcon className="h-4 w-4" /> },
  { id: 'alerts', label: 'Alerts', icon: <AlertTriangle className="h-4 w-4" /> },
]

function SearchPanel({ filters }: { filters: ReturnType<typeof useDiscoveryFilters>['filters'] }) {
  const pipeline = useExecutivePipeline()
  const agencies = pipeline.data?.agencies ?? []

  const filtered = agencies.filter((a) => {
    if (filters.agency !== 'All' && a.agency_code !== filters.agency) return false
    return true
  })

  if (pipeline.isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full rounded-xl" />
        ))}
      </div>
    )
  }

  if (filtered.length === 0) {
    return <EmptyState title="No tenders found" description="Try adjusting your filters or search query." />
  }

  return (
    <div className="space-y-3" role="list" aria-label="Search results">
      {filtered.map((a) => (
        <div key={a.agency_code} role="listitem">
          <TenderCard id={a.agency_code} packageNo={a.agency_code} title={`${a.agency_code} — ${a.live_tenders} live tenders`} agency={a.agency_code} estimatedValue={a.estimated_pipeline_value_bdt} status="live" closingDate={new Date().toISOString()} />
        </div>
      ))}
    </div>
  )
}

function LivePanel() {
  const pipeline = useExecutivePipeline()
  const agencies = pipeline.data?.agencies ?? []
  const [selectedAgency, setSelectedAgency] = useState<string | null>(null)
  const tenders = useQuery({
    queryKey: ['agency-live-tenders', selectedAgency],
    queryFn: () => getAgencyLiveTenders(selectedAgency!),
    enabled: Boolean(selectedAgency),
  })

  if (pipeline.isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full rounded-xl" />
        ))}
      </div>
    )
  }

  const liveItems = agencies.filter((a) => a.live_tenders > 0)

  if (liveItems.length === 0) {
    return <EmptyState title="No live tenders" description="No tenders are currently open for bidding." />
  }

  if (selectedAgency) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-gray-900 dark:text-white">{selectedAgency} live Works tenders</h2>
            <p className="text-xs text-gray-500">{tenders.data?.total ?? 0} individual tenders; estimates are exact APP package matches.</p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => setSelectedAgency(null)}>All agencies</Button>
        </div>
        {tenders.isLoading ? <Skeleton className="h-64 w-full rounded-xl" /> : tenders.error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            Could not load agency tenders. <button className="font-medium underline" onClick={() => tenders.refetch()}>Retry</button>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
            <table className="min-w-[1100px] w-full text-left text-xs">
              <thead className="border-b bg-gray-50 text-gray-500 dark:border-gray-800 dark:bg-gray-800/60">
                <tr>{['Tender ID', 'Package no.', 'Work name', 'PE name', 'Submission last date', 'Tender security', 'APP estimate'].map(label => <th key={label} className="px-3 py-2 font-medium">{label}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {(tenders.data?.tenders ?? []).map(item => (
                  <tr key={item.tender_id} className="align-top hover:bg-blue-50/40 dark:hover:bg-blue-950/20">
                    <td className="px-3 py-3"><Link className="font-mono font-medium text-blue-600 hover:underline" to={`/tender/${item.tender_id}/overview`}>{item.tender_id}</Link></td>
                    <td className="px-3 py-3 font-mono text-gray-700 dark:text-gray-300">{item.package_no || '—'}</td>
                    <td className="max-w-md px-3 py-3 text-gray-900 dark:text-white">{item.work_name || '—'}</td>
                    <td className="px-3 py-3 text-gray-700 dark:text-gray-300">{item.pe_name || '—'}</td>
                    <td className="whitespace-nowrap px-3 py-3">{new Date(item.submission_last_date).toLocaleString()}</td>
                    <td className="whitespace-nowrap px-3 py-3">{item.tender_security_text || formatBdt(item.tender_security_amount_bdt)}<span className="block text-[10px] text-gray-400">{item.tender_security_text ? 'TDS evidence' : 'Not acquired'}</span></td>
                    <td className="whitespace-nowrap px-3 py-3 font-medium">
                      {formatBdt(item.app_estimated_amount_bdt)}
                      <span className="block text-[10px] font-normal text-gray-400">{item.estimate_source ?? 'No APP match'}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-3" role="list" aria-label="Live tenders">
      {liveItems.map((a) => (
        <div key={a.agency_code} role="listitem">
          <TenderCard id={a.agency_code} packageNo={a.agency_code} title={`${a.agency_code} — ${a.live_tenders} live tenders`} agency={a.agency_code} estimatedValue={a.estimated_pipeline_value_bdt} status="live" closingDate={new Date().toISOString()} onClick={() => setSelectedAgency(a.agency_code)} />
        </div>
      ))}
    </div>
  )
}

function formatBdt(value: number | null | undefined) {
  if (value == null || value <= 0) return '—'
  if (value >= 1e7) return `${(value / 1e7).toFixed(2)} Cr BDT`
  if (value >= 1e5) return `${(value / 1e5).toFixed(2)} L BDT`
  return `${value.toLocaleString()} BDT`
}

function EnrichmentQueuePanel() {
  const queryClient = useQueryClient()
  const queue = useQuery({
    queryKey: ['live-enrichment-queue'],
    queryFn: getLiveEnrichmentQueue,
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? []
      return items.some(item => item.status === 'running') ? 3000 : 15000
    },
  })
  const refresh = useMutation({
    mutationFn: () => refreshLiveEnrichmentQueue(20, 10_000_000),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['live-enrichment-queue'] }),
  })
  const run = useMutation({
    mutationFn: () => runLiveEnrichmentQueue(3),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['live-enrichment-queue'] }),
  })
  const counts = queue.data?.counts ?? {}

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <h2 className="font-semibold text-gray-900 dark:text-white">Live Tender Enrichment Queue</h2>
            <p className="mt-1 text-xs text-gray-500">Works-only tenders worth at least 1 crore. Acquires Notice/TDS, extracts requirements and security, and keeps exact APP package estimates.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => refresh.mutate()} disabled={refresh.isPending}>
              {refresh.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Database className="mr-1 h-4 w-4" />}
              Find high-value tenders
            </Button>
            <Button size="sm" onClick={() => run.mutate()} disabled={run.isPending || !(counts.queued || counts.failed)}>
              {run.isPending ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Play className="mr-1 h-4 w-4" />}
              Enrich next 3
            </Button>
          </div>
        </div>
        <div className="grid grid-cols-4 border-t border-gray-100 dark:border-gray-800">
          {(['queued', 'running', 'completed', 'failed'] as const).map(status => (
            <div key={status} className="p-3 text-center">
              <div className="text-lg font-semibold text-gray-900 dark:text-white">{counts[status] ?? 0}</div>
              <div className="text-[10px] uppercase tracking-wide text-gray-500">{status}</div>
            </div>
          ))}
        </div>
      </Card>
      {(refresh.error || run.error) && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {(refresh.error || run.error)?.message}
        </div>
      )}
      {queue.isLoading ? <Skeleton className="h-64 w-full rounded-xl" /> : (queue.data?.items.length ?? 0) === 0 ? (
        <EmptyState title="Queue is empty" description="Find high-value live Works tenders to create the first enrichment batch." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
          <table className="min-w-[1050px] w-full text-left text-xs">
            <thead className="border-b bg-gray-50 text-gray-500 dark:border-gray-800 dark:bg-gray-800/60">
              <tr>{['Priority', 'Tender', 'Agency / package', 'APP estimate', 'Deadline', 'Status', 'Quality gate', 'Extracted output'].map(label => <th key={label} className="px-3 py-2 font-medium">{label}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {(queue.data?.items ?? []).map(item => (
                <tr key={item.id} className="align-top">
                  <td className="px-3 py-3 font-semibold">{item.priority_score.toFixed(1)}</td>
                  <td className="max-w-sm px-3 py-3"><Link to={`/tender/${item.tender_id}/overview`} className="font-mono font-medium text-blue-600 hover:underline">{item.tender_id}</Link><span className="mt-1 block text-gray-700 dark:text-gray-300">{item.title || '—'}</span></td>
                  <td className="px-3 py-3"><span className="font-medium">{item.agency_code || 'UNKNOWN'}</span><span className="block font-mono text-gray-500">{item.package_no || '—'}</span></td>
                  <td className="whitespace-nowrap px-3 py-3 font-medium">{formatBdt(item.app_estimated_amount_bdt)}<span className="block text-[10px] font-normal text-gray-400">{item.estimate_source || 'No match'}</span></td>
                  <td className="whitespace-nowrap px-3 py-3">{item.closing_datetime ? new Date(item.closing_datetime).toLocaleString() : '—'}</td>
                  <td className="px-3 py-3"><span className={`rounded-full px-2 py-1 text-[10px] font-medium ${item.status === 'completed' ? 'bg-green-100 text-green-700' : item.status === 'failed' ? 'bg-red-100 text-red-700' : item.status === 'running' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>{item.status}</span>{item.error && <span className="mt-1 block max-w-xs text-[10px] text-red-600">{item.error}</span>}</td>
                  <td className="px-3 py-3"><span className={`rounded-full px-2 py-1 text-[10px] font-medium ${item.quality_status === 'passed' ? 'bg-green-100 text-green-700' : item.quality_status === 'blocked' ? 'bg-red-100 text-red-700' : item.quality_status === 'warning' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}`}>{item.quality_status.replace('_', ' ')}</span><span className="mt-1 block text-[10px] text-gray-500">{item.quality_score == null ? 'Not scored' : `${item.quality_score}/100`} · {item.quality_critical_count} critical / {item.quality_warning_count} warnings</span></td>
                  <td className="px-3 py-3">{item.requirements_count} criteria<span className="block text-gray-500">{item.tender_security_text || 'Security pending'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function BidShortlistPanel() {
  const [contractor, setContractor] = useState(() => localStorage.getItem('procureflow-shortlist-contractor') || '')
  const [appliedContractor, setAppliedContractor] = useState(contractor)
  const shortlist = useQuery({
    queryKey: ['bid-shortlist', appliedContractor],
    queryFn: () => getBidShortlist(appliedContractor || undefined),
  })
  const applyProfile = () => {
    localStorage.setItem('procureflow-shortlist-contractor', contractor.trim())
    setAppliedContractor(contractor.trim())
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="p-4">
          <h2 className="font-semibold text-gray-900 dark:text-white">Bid / No-Bid Shortlist</h2>
          <p className="mt-1 text-xs text-gray-500">Ranks live Works tenders using company experience, capacity, location, APP value, extracted eligibility, competition and expected profit.</p>
          <div className="mt-3 flex max-w-xl gap-2">
            <Input value={contractor} onChange={event => setContractor(event.target.value)} placeholder="Canonical contractor ID or company name" onKeyDown={event => event.key === 'Enter' && applyProfile()} />
            <Button onClick={applyProfile}>Apply company</Button>
          </div>
          {shortlist.data?.profile ? <p className="mt-2 text-xs text-green-700">Scoring against {shortlist.data.profile.display_name}</p> : <p className="mt-2 text-xs text-amber-700">Neutral scores are shown until a company profile is selected.</p>}
        </div>
      </Card>
      {shortlist.isLoading ? <Skeleton className="h-64 w-full rounded-xl" /> : shortlist.error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{shortlist.error.message}</div>
      ) : (
        <div className="space-y-3">
          {(shortlist.data?.items ?? []).map(item => (
            <Card key={item.tender_id}>
              <div className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="max-w-2xl">
                    <div className="flex items-center gap-2"><Link to={`/tender/${item.tender_id}/overview`} className="font-mono text-sm font-semibold text-blue-600 hover:underline">{item.tender_id}</Link><span className="rounded bg-gray-100 px-2 py-0.5 text-[10px]">{item.agency_code}</span></div>
                    <p className="mt-1 text-sm text-gray-900 dark:text-white">{item.title}</p>
                    <p className="mt-1 text-xs text-gray-500">{item.package_no} · {item.district || 'Location pending'} · {formatBdt(item.app_estimated_amount_bdt)}</p>
                  </div>
                  <div className="text-right"><div className="text-2xl font-bold">{item.score}</div><span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${item.decision === 'BID' ? 'bg-green-100 text-green-700' : item.decision === 'NO-BID' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{item.decision}</span></div>
                </div>
                <div className="mt-3 grid grid-cols-4 gap-2 sm:grid-cols-8">
                  {Object.entries(item.score_breakdown).map(([label, value]) => <div key={label} className="rounded bg-gray-50 p-2 text-center dark:bg-gray-800"><div className="font-semibold">{value}</div><div className="text-[9px] capitalize text-gray-500">{label.replace('_', ' ')}</div></div>)}
                </div>
              </div>
            </Card>
          ))}
          {(shortlist.data?.items.length ?? 0) === 0 && <EmptyState title="No tenders to rank" description="Populate the enrichment queue first." />}
        </div>
      )}
    </div>
  )
}

function RadarPanel() {
  const { data, isLoading } = useRecentAgentResults(20)
  return (
    <RadarFeed results={data?.results ?? []} isLoading={isLoading} />
  )
}

function AlertsPanel() {
  const queryClient = useQueryClient()
  const alerts = useQuery({ queryKey: ['tender-alerts'], queryFn: getTenderAlerts, refetchInterval: 30_000 })
  const [form, setForm] = useState({
    name: 'High-value Works',
    agencies: '',
    districts: '',
    min_value_crore: 1,
    max_value_crore: 0,
    work_types: 'Works',
    eligibility_keywords: '',
    deadline_days: 30,
  })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['tender-alerts'] })
  const createFilter = useMutation({
    mutationFn: () => createTenderAlertFilter({
      name: form.name,
      agencies: form.agencies.split(',').map(value => value.trim().toUpperCase()).filter(Boolean),
      districts: form.districts.split(',').map(value => value.trim()).filter(Boolean),
      min_value_bdt: Number(form.min_value_crore || 0) * 10_000_000,
      max_value_bdt: Number(form.max_value_crore || 0) > 0 ? Number(form.max_value_crore) * 10_000_000 : null,
      work_types: form.work_types.split(',').map(value => value.trim()).filter(Boolean),
      eligibility_keywords: form.eligibility_keywords.split(',').map(value => value.trim()).filter(Boolean),
      deadline_days: Number(form.deadline_days),
      active: true,
    }),
    onSuccess: refresh,
  })
  const evaluate = useMutation({ mutationFn: evaluateTenderAlerts, onSuccess: refresh })
  const remove = useMutation({ mutationFn: deleteTenderAlertFilter, onSuccess: refresh })
  const markRead = useMutation({ mutationFn: markTenderAlertRead, onSuccess: refresh })

  return (
    <div className="space-y-4">
      <Card title="Saved Tender Alert">
        <div className="mb-3 flex justify-end"><Button size="sm" variant="secondary" onClick={() => evaluate.mutate()} disabled={evaluate.isPending} leftIcon={<RefreshCw size={14} />}>{evaluate.isPending ? 'Matching…' : 'Check now'}</Button></div>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <label className="text-xs text-gray-500">Alert name<input value={form.name} onChange={event => setForm(current => ({ ...current, name: event.target.value }))} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" /></label>
          <label className="text-xs text-gray-500">Agencies, comma separated<input value={form.agencies} onChange={event => setForm(current => ({ ...current, agencies: event.target.value }))} placeholder="BWDB, LGED, PWD" className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" /></label>
          <label className="text-xs text-gray-500">Districts<input value={form.districts} onChange={event => setForm(current => ({ ...current, districts: event.target.value }))} placeholder="Dhaka, Cox's Bazar" className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" /></label>
          <label className="text-xs text-gray-500">Deadline within days<input type="number" min="1" max="365" value={form.deadline_days} onChange={event => setForm(current => ({ ...current, deadline_days: Number(event.target.value) }))} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" /></label>
          <label className="text-xs text-gray-500">Minimum value (Cr)<input type="number" min="0" step="0.1" value={form.min_value_crore} onChange={event => setForm(current => ({ ...current, min_value_crore: Number(event.target.value) }))} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" /></label>
          <label className="text-xs text-gray-500">Maximum value (Cr, 0 = any)<input type="number" min="0" step="0.1" value={form.max_value_crore} onChange={event => setForm(current => ({ ...current, max_value_crore: Number(event.target.value) }))} className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" /></label>
          <label className="text-xs text-gray-500">Work types<input value={form.work_types} onChange={event => setForm(current => ({ ...current, work_types: event.target.value }))} placeholder="Works, bridge, road" className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" /></label>
          <label className="text-xs text-gray-500">Eligibility keywords<input value={form.eligibility_keywords} onChange={event => setForm(current => ({ ...current, eligibility_keywords: event.target.value }))} placeholder="turnover, liquid assets" className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900" /></label>
        </div>
        <Button className="mt-4" onClick={() => createFilter.mutate()} disabled={!form.name.trim() || createFilter.isPending} leftIcon={<Bell size={14} />}>{createFilter.isPending ? 'Saving & matching…' : 'Save alert and match live tenders'}</Button>
        {createFilter.data && <p className="mt-2 text-xs text-green-700">{createFilter.data.matches} current matches · {createFilter.data.notifications_created} new notifications</p>}
        {(createFilter.error || evaluate.error) && <p className="mt-2 text-xs text-red-600">{(createFilter.error || evaluate.error)?.message}</p>}
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title={`Saved Filters (${alerts.data?.filters.length ?? 0})`}>
          <div className="space-y-2">{alerts.data?.filters.map(filter => <div key={filter.id} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700"><div className="flex items-start justify-between gap-2"><div><p className="text-sm font-semibold">{filter.name}</p><p className="mt-1 text-xs text-gray-500">{filter.agencies.length ? filter.agencies.join(', ') : 'All agencies'} · {filter.districts.length ? filter.districts.join(', ') : 'All districts'} · {filter.deadline_days} days</p><p className="mt-1 text-xs text-blue-600">{filter.last_match_count || 0} matched notifications · minimum {formatBdt(filter.min_value_bdt)}</p></div><button aria-label={`Delete ${filter.name}`} onClick={() => remove.mutate(filter.id)} className="rounded p-1 text-red-500 hover:bg-red-50"><Trash2 size={14} /></button></div></div>)}</div>
          {!alerts.isLoading && !alerts.data?.filters.length && <p className="text-sm text-gray-500">No saved filters yet.</p>}
        </Card>
        <div className="lg:col-span-2"><Card title={`Dashboard Notifications (${alerts.data?.unread ?? 0} unread)`}>
          <div className="max-h-[560px] space-y-2 overflow-auto">{alerts.data?.notifications.map(notification => <div key={notification.id} className={`w-full rounded-lg border p-3 text-left ${notification.read ? 'border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900' : 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30'}`}><div className="flex justify-between gap-3"><div><div className="flex items-center gap-2"><Link to={`/tender/${notification.tender_id}/overview`} className="font-mono text-xs font-semibold text-blue-600">{notification.tender_id}</Link><span className="rounded bg-gray-100 px-2 py-0.5 text-[10px]">{notification.agency_code}</span><span className="text-[10px] text-gray-500">{notification.filter_name}</span></div><p className="mt-1 text-sm font-medium">{notification.title}</p><p className="mt-1 text-xs text-gray-500">{notification.package_no || 'Package pending'} · {notification.district || 'District pending'} · closes {notification.closing_datetime ? new Date(notification.closing_datetime).toLocaleDateString() : 'pending'}</p></div><div className="text-right"><p className="whitespace-nowrap text-sm font-semibold">{formatBdt(notification.estimated_cost_bdt)}</p>{!notification.read && <button onClick={() => markRead.mutate(notification.id)} className="mt-2 text-xs font-medium text-blue-600">Mark read</button>}</div></div></div>)}</div>
          {!alerts.isLoading && !alerts.data?.notifications.length && <p className="text-sm text-gray-500">Saved filters will create notifications when live Works tenders match.</p>}
        </Card></div>
      </div>
    </div>
  )
}

function TenderPipelineTrigger() {
  const [tenderId, setTenderId] = useState('')
  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [tenderData, setTenderData] = useState<any>(null)
  const [isLoadingTender, setIsLoadingTender] = useState(false)
  const [runResult, setRunResult] = useState<any>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { registeredAgents } = useAgents()
  const runAgentMutation = useRunAgent()

  const availableAgents = registeredAgents.filter(a => a.available)

  async function fetchTender() {
    if (!tenderId.trim()) return
    setIsLoadingTender(true)
    setError(null)
    setTenderData(null)
    try {
      const data = await fetchJson<any>(`/api/tender/${tenderId}`, true)
      setTenderData(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch tender')
    } finally {
      setIsLoadingTender(false)
    }
  }

  async function triggerPipeline() {
    if (!selectedAgentId) return
    setIsRunning(true)
    setRunResult(null)
    setError(null)
    try {
      const result = await runAgentMutation.mutateAsync({
        agentId: selectedAgentId,
        input: { tender_id: tenderId }
      })
      setRunResult(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run pipeline')
    } finally {
      setIsRunning(false)
    }
  }

  const agentInfo = availableAgents.find(a => a.id === selectedAgentId)

  return (
    <div className="space-y-4">
      <Card padding="md" className="space-y-4">
        <div className="flex items-center gap-2">
          <ZapIcon className="h-5 w-5 text-blue-600" />
          <h3 className="font-semibold text-gray-900 dark:text-white">Tender ID Search & Pipeline Trigger</h3>
        </div>
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Enter Tender ID (e.g., 1298004)"
              value={tenderId}
              onChange={e => setTenderId(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && fetchTender()}
              className="flex-1"
            />
            <Button onClick={fetchTender} disabled={isLoadingTender || !tenderId.trim()}>
              {isLoadingTender ? <Loader2 className="h-4 w-4 animate-spin" /> : <SearchIcon className="h-4 w-4" />}
            </Button>
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              {error}
            </div>
          )}

          {tenderData && (
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
              <h3 className="mb-2 font-medium text-gray-900 dark:text-white">Tender Details</h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
                <div><span className="text-gray-500">Tender ID:</span> <span className="ml-2 font-mono font-medium">{tenderData.tender_id ?? tenderId}</span></div>
                <div><span className="text-gray-500">Title:</span> <span className="ml-2 truncate block">{tenderData.title ?? tenderData.variables?.title ?? '—'}</span></div>
                <div><span className="text-gray-500">Agency:</span> <span className="ml-2">{tenderData.procuring_entity ?? tenderData.variables?.procuring_entity ?? '—'}</span></div>
                <div><span className="text-gray-500">Est. Cost:</span> <span className="ml-2 tabular-nums">{tenderData.estimated_cost_bdt ? `BDT ${tenderData.estimated_cost_bdt.toLocaleString()}` : '—'}</span></div>
                <div className="sm:col-span-2"><span className="text-gray-500">District/Division:</span> <span className="ml-2">{tenderData.district ?? '—'} / {tenderData.division ?? '—'}</span></div>
              </div>
            </div>
          )}

          <div className="space-y-3">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Select Pipeline Agent</label>
            <select
              value={selectedAgentId}
              onChange={e => setSelectedAgentId(e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {availableAgents.map(a => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>

            {agentInfo && (
              <p className="text-xs text-gray-500 dark:text-gray-400">{agentInfo.description}</p>
            )}

            <Button 
              onClick={triggerPipeline} 
              disabled={isRunning || !tenderData || !selectedAgentId}
              className="w-full"
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Running pipeline...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Pipeline on Tender
                </>
              )}
            </Button>

            {runResult && (
              <div className="rounded-xl border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-950/20">
                <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                  <CheckCircle className="h-5 w-5" />
                  <span className="font-medium">Pipeline triggered successfully</span>
                </div>
                <pre className="mt-2 text-xs bg-white/50 dark:bg-gray-800/50 p-2 rounded overflow-auto max-h-40">
                  {JSON.stringify(runResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}

export function DiscoveryPage() {
  const { filters, setFilter, clearFilters, hasActiveFilters } = useDiscoveryFilters()
  const [searchParams, setSearchParams] = useSearchParams()

  const activeTab = searchParams.get('tab') ?? 'search'

  function setTab(tab: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('tab', tab)
      return next
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Opportunity Discovery</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Search, monitor, and receive alerts for tender opportunities
        </p>
      </div>

      <FilterBar
        filters={filters}
        onFilterChange={setFilter}
        onClear={clearFilters}
        hasActive={hasActiveFilters}
      />

      <Tabs value={activeTab} onValueChange={setTab}>
        <TabsList>
          {TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              {tab.icon}
              <span className="ml-2">{tab.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="search">
          <SearchPanel filters={filters} />
        </TabsContent>

        <TabsContent value="live">
          <LivePanel />
        </TabsContent>

        <TabsContent value="enrichment">
          <EnrichmentQueuePanel />
        </TabsContent>

        <TabsContent value="shortlist">
          <BidShortlistPanel />
        </TabsContent>

        <TabsContent value="radar">
          <RadarPanel />
        </TabsContent>

        <TabsContent value="pipeline">
          <TenderPipelineTrigger />
        </TabsContent>

        <TabsContent value="alerts">
          <AlertsPanel />
        </TabsContent>
      </Tabs>
    </div>
  )
}
