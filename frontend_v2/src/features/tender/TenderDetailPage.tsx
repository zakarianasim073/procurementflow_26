import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, FileText, Download, Building2, MapPin, Award, DollarSign, Shield, TrendingUp } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import { useTenderDetail, useTenderBrainDetail } from '@hooks/index'

export function TenderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const detail = useTenderDetail(id ?? '')
  const brain = useTenderBrainDetail(id ?? '')

  const isLoading = detail.isLoading || brain.isLoading
  const error = detail.error || brain.error
  const brainUnavailable = brain.data === null
  const isNotFound =
    !isLoading && !error && brain.data && !brain.data.tender && !brainUnavailable

  const docLinks = detail.data?.documents ?? {}
  const variables = detail.data?.variables ?? {} as Record<string, unknown>
  const brainData = brain.data
  const tenderMeta = brainData?.tender
  const award = brainData?.award

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
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                {isLoading ? 'Loading...' : (tenderMeta?.title || (variables.title as string) || `Tender ${id}`)}
              </h1>
            </div>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">Tender detail &amp; documents</p>
          </div>
        </div>
      }
      primary={
        <>
          {isLoading ? (
            <TenderDetailSkeleton />
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              Failed to load tender data.{' '}
              <button onClick={() => { detail.refetch(); brain.refetch() }} className="font-medium underline">
                Retry
              </button>
            </div>
          ) : isNotFound ? (
            <div className="rounded-xl border border-gray-200 bg-white p-8 text-center dark:border-gray-800 dark:bg-gray-900">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Tender &quot;{id}&quot; not found.{' '}
                <Link to="/tender" className="font-medium text-blue-600 hover:underline dark:text-blue-400">
                  Back to tenders
                </Link>
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Info cards */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {tenderMeta?.agency && (
                  <InfoCard icon={Building2} label="Agency" value={tenderMeta.agency} />
                )}
                {tenderMeta?.zone && (
                  <InfoCard icon={MapPin} label="Zone" value={tenderMeta.zone} />
                )}
                {tenderMeta?.procurement_method && (
                  <InfoCard icon={TrendingUp} label="Method" value={tenderMeta.procurement_method} />
                )}
                {tenderMeta?.pe_office && (
                  <InfoCard icon={MapPin} label="PE Office" value={tenderMeta.pe_office} />
                )}
                {!!variables.estimated_cost && (
                  <InfoCard icon={DollarSign} label="Est. Cost" value={String(variables.estimated_cost)} />
                )}
                {!!variables.tender_security && (
                  <InfoCard icon={Shield} label="Tender Security" value={String(variables.tender_security)} />
                )}
              </div>

              {/* Documents */}
              <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Documents</h2>
                {Object.keys(docLinks).length === 0 ? (
                  <p className="text-sm text-gray-400">No documents available for this tender.</p>
                ) : (
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(docLinks).map(([type, _filename]) => (
                      <a
                        key={type}
                        href={`/api/tender/${id}/document/${type}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3 text-sm transition-colors hover:border-blue-200 hover:bg-blue-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-blue-700 dark:hover:bg-blue-900/20"
                      >
                        <FileText size={16} className="shrink-0 text-blue-500" />
                        <span className="flex-1 truncate font-medium text-gray-700 dark:text-gray-300">
                          {type.toUpperCase()}
                        </span>
                        <Download size={14} className="shrink-0 text-gray-400" />
                      </a>
                    ))}
                  </div>
                )}
              </div>

              {/* Award info */}
              {award && (
                <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                  <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">
                    <Award size={14} className="mr-1.5 inline text-yellow-500" />
                    Award Information
                  </h2>
                  <div className="grid grid-cols-2 gap-3">
                    <InfoCard icon={Building2} label="Contractor" value={award.contractor_name} />
                    <InfoCard icon={DollarSign} label="Award Amount" value={`${(award.award_amount / 1e7).toFixed(1)}Cr`} />
                  </div>
                </div>
              )}

              {/* Variables */}
              {Object.keys(variables).length > 0 && (
                <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                  <h2 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Extracted Data</h2>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
                    {Object.entries(variables).filter(([k]) => !['title', 'estimated_cost', 'tender_security', 'procuring_entity'].includes(k)).map(([key, val]) => (
                      <div key={key} className="text-sm">
                        <span className="text-xs text-gray-500 dark:text-gray-400">{key.replace(/_/g, ' ')}</span>
                        <p className="truncate font-medium text-gray-800 dark:text-gray-200">
                          {typeof val === 'object' ? JSON.stringify(val).slice(0, 60) : String(val)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      }
    />
  )
}

function InfoCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
        <Icon size={14} />
        {label}
      </div>
      <p className="mt-1 text-sm font-medium text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

function TenderDetailSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800/60" />
        ))}
      </div>
      <div className="h-32 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-800/60" />
    </div>
  )
}
