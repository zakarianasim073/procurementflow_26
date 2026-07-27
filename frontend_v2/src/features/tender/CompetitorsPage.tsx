import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card } from '@shared/ui/Card'
import { Badge } from '@shared/ui/Badge'
import { Input } from '@shared/ui/Input'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { ScreenTemplate } from '@layouts/index'
import { useCompetitors } from '@hooks/index'

function TrendIcon({ value }: { value: number }) {
  if (value > 0) return <TrendingUp className="h-4 w-4 text-green-500" />
  if (value < 0) return <TrendingDown className="h-4 w-4 text-red-500" />
  return <Minus className="h-4 w-4 text-gray-400" />
}

export function CompetitorsPage() {
  const navigate = useNavigate()
  const [tenderId, setTenderId] = useState('')

  const { data: competitors, isLoading, error, refetch } = useCompetitors(tenderId ? { search: tenderId } : undefined)

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/tender')} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Competitor Intelligence</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Analyze competitor bid patterns and win rates</p>
          </div>
        </div>
      }
      primary={
        <div className="space-y-6">
          <Card className="p-4">
            <Input
              label="Filter by Tender ID"
              value={tenderId}
              onChange={(e) => setTenderId(e.target.value)}
              placeholder="Optional: filter by specific tender"
              className="w-64"
            />
          </Card>

          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              Competitor data could not be loaded.{' '}
              <button type="button" className="font-medium underline" onClick={() => refetch()}>Retry</button>
            </div>
          ) : !competitors?.length ? (
            <EmptyState
              title="No competitor data"
              description="Competitor intelligence will appear as tenders are analyzed."
            />
          ) : (
            <div className="space-y-4">
              {competitors.map((comp) => (
                <Card key={comp.competitor_id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{comp.name}</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {comp.total_bids} bids · {comp.total_wins} wins
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <TrendIcon value={comp.win_rate - 50} />
                      <Badge tone={comp.win_rate > 60 ? 'success' : comp.win_rate > 40 ? 'warning' : 'danger'}>
                        {comp.win_rate.toFixed(0)}% win rate
                      </Badge>
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
                      <span className="text-gray-500">Avg Discount</span>
                      <p className="font-medium text-gray-900 dark:text-white">{comp.avg_discount.toFixed(1)}%</p>
                    </div>
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
                      <span className="text-gray-500">Specialties</span>
                      <p className="font-medium text-gray-900 dark:text-white">{comp.specialties.length}</p>
                    </div>
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
                      <span className="text-gray-500">Agencies</span>
                      <p className="font-medium text-gray-900 dark:text-white">{comp.agencies.length}</p>
                    </div>
                  </div>

                  {comp.specialties.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {comp.specialties.map((s) => (
                        <span key={s} className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}

                  {comp.recent_activity.length > 0 && (
                    <div className="mt-3">
                      <p className="mb-2 text-xs font-medium text-gray-500 dark:text-gray-400">Recent Activity</p>
                      <div className="space-y-1">
                        {comp.recent_activity.slice(0, 3).map((act) => (
                          <div key={act.tender_id} className="flex items-center justify-between text-xs">
                            <span className="text-gray-600 dark:text-gray-400 truncate">{act.title}</span>
                            <Badge tone={act.status === 'won' ? 'success' : act.status === 'lost' ? 'danger' : 'default'}>
                              {act.status}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      }
    />
  )
}
