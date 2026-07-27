import { useState } from 'react'
import {
  useMarketOverview,
  useAwardHistory,
  useAgencyBehaviour,
  useTopContractors,
  useNppiAnalysis,
} from '@hooks/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { bdt, count, nppiPct, nppiTone } from './marketFormat'

const CARD =
  'rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900'
const CELL = 'rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60'
const TH = 'px-3 py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400'
const TD = 'px-3 py-2 text-sm text-gray-700 dark:text-gray-300'

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className={CARD}>
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{title}</h2>
        {hint && <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{hint}</p>}
      </div>
      {children}
    </div>
  )
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className={CELL}>
      <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
      <p className="text-lg font-bold tabular-nums text-gray-900 dark:text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 dark:text-gray-400">{sub}</p>}
    </div>
  )
}

/** Horizontal bar sized against the largest value in its group. */
function Bar({ value, max, tone = 'bg-blue-500' }: { value: number; max: number; tone?: string }) {
  const pct = max > 0 ? Math.max(2, (value / max) * 100) : 0
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
      <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function OverviewSection() {
  const { data, isLoading } = useMarketOverview()
  if (isLoading) return <Skeleton className="h-32 w-full rounded-xl" />
  if (!data) return null

  return (
    <Section title="Market Overview" hint="Across the full procurement lifecycle record">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        <Stat label="Lifecycle Records" value={count(data.total_records)} />
        <Stat label="Awards" value={count(data.awarded_count)} />
        <Stat label="Total Awarded" value={bdt(data.total_awarded_bdt)} />
        <Stat label="Median Award" value={bdt(data.median_award_bdt)} sub={`avg ${bdt(data.avg_award_bdt)}`} />
        <Stat label="Agencies" value={count(data.agency_count)} />
        <Stat label="Contractors" value={count(data.contractor_count)} />
      </div>
      {data.median_nppi != null && (
        <div className="mt-3 rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Median NPPI — awards land at this share of the published estimate
          </span>
          <p className={`text-lg font-bold tabular-nums ${nppiTone(data.median_nppi)}`}>
            {nppiPct(data.median_nppi)}
            <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">
              from {count(data.nppi_sample)} tenders with both an estimate and an award
            </span>
          </p>
        </div>
      )}
    </Section>
  )
}

function AwardHistorySection() {
  const { data, isLoading } = useAwardHistory(8)
  if (isLoading) return <Skeleton className="h-56 w-full rounded-xl" />
  if (!data?.length) return <EmptyState title="No award history" description="No awards carry a usable date and amount." />

  const maxValue = Math.max(...data.map(d => d.total_value_bdt ?? 0))

  return (
    <Section title="Award History" hint="Volume, value and negotiated discount by year">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-gray-200 dark:border-gray-800">
            <tr>
              <th className={TH}>Year</th>
              <th className={TH}>Awards</th>
              <th className={TH}>Total Value</th>
              <th className={TH}>Avg</th>
              <th className={TH}>Contractors</th>
              <th className={TH}>Median NPPI</th>
              <th className={`${TH} w-32`}>Share</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {data.map(y => (
              <tr key={y.year}>
                <td className={`${TD} font-medium text-gray-900 dark:text-white`}>{y.year}</td>
                <td className={`${TD} tabular-nums`}>{count(y.award_count)}</td>
                <td className={`${TD} tabular-nums`}>{bdt(y.total_value_bdt)}</td>
                <td className={`${TD} tabular-nums`}>{bdt(y.avg_value_bdt)}</td>
                <td className={`${TD} tabular-nums`}>{count(y.contractor_count)}</td>
                <td className={`${TD} tabular-nums font-medium ${nppiTone(y.median_nppi)}`}>
                  {nppiPct(y.median_nppi)}
                </td>
                <td className="px-3 py-2">
                  <Bar value={y.total_value_bdt ?? 0} max={maxValue} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  )
}

function AgencySection() {
  const { data, isLoading } = useAgencyBehaviour(12)
  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />
  if (!data?.length) return null

  const maxCount = Math.max(...data.map(a => a.award_count))

  return (
    <Section
      title="Agency Behaviour"
      hint="How each buyer awards — typical size, discount, and how concentrated its supplier base is"
    >
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-gray-200 dark:border-gray-800">
            <tr>
              <th className={TH}>Agency</th>
              <th className={TH}>Awards</th>
              <th className={TH}>Total</th>
              <th className={TH}>Median Size</th>
              <th className={TH}>Suppliers</th>
              <th className={TH}>Median NPPI</th>
              <th className={TH}>Leading Contractor</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {data.map(a => (
              <tr key={a.agency_code}>
                <td className={`${TD} font-medium text-gray-900 dark:text-white`}>
                  {a.agency_code.trim()}
                  <Bar value={a.award_count} max={maxCount} />
                </td>
                <td className={`${TD} tabular-nums`}>{count(a.award_count)}</td>
                <td className={`${TD} tabular-nums`}>{bdt(a.total_value_bdt)}</td>
                <td className={`${TD} tabular-nums`}>{bdt(a.median_value_bdt)}</td>
                <td className={`${TD} tabular-nums`}>{count(a.contractor_count)}</td>
                <td className={`${TD} tabular-nums font-medium ${nppiTone(a.median_nppi)}`}>
                  {nppiPct(a.median_nppi)}
                </td>
                <td className={TD}>
                  {a.top_contractor ? (
                    <span title={`${a.top_wins} of ${a.award_count} awards`}>
                      <span className="block max-w-[14rem] truncate">{a.top_contractor}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {a.contractor_concentration_pct ?? 0}% of awards
                      </span>
                    </span>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  )
}

function ContractorSection() {
  const [limit, setLimit] = useState(15)
  const { data, isLoading } = useTopContractors(limit)
  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />
  if (!data?.length) return null

  return (
    <Section
      title="Contractors & Competitors"
      hint="Most active winners, how widely they operate, and the discount they typically bid at"
    >
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-gray-200 dark:border-gray-800">
            <tr>
              <th className={TH}>Contractor</th>
              <th className={TH}>Wins</th>
              <th className={TH}>Total Value</th>
              <th className={TH}>Avg</th>
              <th className={TH}>Largest</th>
              <th className={TH}>Agencies</th>
              <th className={TH}>Latest</th>
              <th className={TH}>Median NPPI</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {data.map(c => (
              <tr key={c.contractor_name}>
                <td className={`${TD} font-medium text-gray-900 dark:text-white`}>
                  <span className="block max-w-[18rem] truncate" title={c.contractor_name}>
                    {c.contractor_name}
                  </span>
                </td>
                <td className={`${TD} tabular-nums`}>{count(c.win_count)}</td>
                <td className={`${TD} tabular-nums`}>{bdt(c.total_value_bdt)}</td>
                <td className={`${TD} tabular-nums`}>{bdt(c.avg_value_bdt)}</td>
                <td className={`${TD} tabular-nums`}>{bdt(c.largest_award_bdt)}</td>
                <td className={`${TD} tabular-nums`}>{count(c.agency_count)}</td>
                <td className={`${TD} tabular-nums`}>{c.latest_award_year ?? '—'}</td>
                <td className={`${TD} tabular-nums font-medium ${nppiTone(c.median_nppi)}`}>
                  {nppiPct(c.median_nppi)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {limit < 50 && (
        <button
          onClick={() => setLimit(50)}
          className="mt-3 text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
        >
          Show more contractors
        </button>
      )}
    </Section>
  )
}

function NppiSection() {
  const { data, isLoading } = useNppiAnalysis()
  if (isLoading) return <Skeleton className="h-56 w-full rounded-xl" />
  if (!data?.summary?.sample_size) return null

  const { summary, distribution, by_agency } = data
  const maxBucket = Math.max(...distribution.map(b => b.count))

  return (
    <Section
      title="NPPI — Award vs Estimate"
      hint={`Award as a share of the published estimate, over ${count(summary.sample_size)} tenders carrying both figures. Below 100% means the award came in under estimate.`}
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {([['P10', summary.p10], ['P25', summary.p25], ['Median', summary.median], ['P75', summary.p75], ['P90', summary.p90]] as const).map(
          ([label, v]) => (
            <div key={label} className={CELL}>
              <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
              <p className={`text-base font-bold tabular-nums ${nppiTone(v)}`}>{nppiPct(v)}</p>
            </div>
          ),
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Distribution</h3>
          <div className="space-y-2">
            {distribution.map(b => (
              <div key={b.bucket} className="flex items-center gap-3">
                <span className="w-20 shrink-0 text-xs text-gray-600 dark:text-gray-400">{b.bucket}</span>
                <div className="flex-1"><Bar value={b.count} max={maxBucket} tone="bg-emerald-500" /></div>
                <span className="w-14 shrink-0 text-right text-xs tabular-nums text-gray-500 dark:text-gray-400">
                  {count(b.count)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-2 text-xs font-medium uppercase text-gray-500 dark:text-gray-400">By Agency</h3>
          <div className="space-y-1.5">
            {by_agency.slice(0, 10).map(a => (
              <div key={a.agency_code} className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate text-gray-700 dark:text-gray-300">{a.agency_code.trim()}</span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="text-gray-400 dark:text-gray-600">n={count(a.sample_size)}</span>
                  <span className={`w-14 text-right font-medium tabular-nums ${nppiTone(a.median_nppi)}`}>
                    {nppiPct(a.median_nppi)}
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Section>
  )
}

export function MarketResearchPanel() {
  return (
    <div className="space-y-4">
      <OverviewSection />
      <NppiSection />
      <AwardHistorySection />
      <AgencySection />
      <ContractorSection />
    </div>
  )
}
