import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Award } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { Card } from '@shared/ui/Card'
import { Badge } from '@shared/ui/Badge'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { ScreenTemplate } from '@layouts/index'
import { useAwards, useAwardStats } from '@hooks/index'

export function AwardPage() {
  const navigate = useNavigate()

  const { data: awards, isLoading: awardsLoading } = useAwards()
  const { data: stats, isLoading: statsLoading } = useAwardStats()

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/tender')} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Award Analysis</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Track awards, variance analysis, and contractor performance</p>
          </div>
        </div>
      }
      primary={
        <div className="space-y-6">
          {/* Stats */}
          {statsLoading ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
            </div>
          ) : stats && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Card className="p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Total Awards</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total_awards}</p>
              </Card>
              <Card className="p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Total Value</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  ৳{(stats.total_awarded_amount / 1e7).toFixed(1)}Cr
                </p>
              </Card>
              <Card className="p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Avg Variance</p>
                <p className={cn(
                  'text-2xl font-bold',
                  stats.avg_variance_pct < 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                )}>
                  {stats.avg_variance_pct > 0 ? '+' : ''}{stats.avg_variance_pct.toFixed(1)}%
                </p>
              </Card>
              <Card className="p-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">Agencies</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.top_entities?.length ?? 0}</p>
              </Card>
            </div>
          )}

          {/* Awards List */}
          {awardsLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
            </div>
          ) : !awards?.length ? (
            <EmptyState
              title="No awards found"
              description="Award data will appear when tenders are awarded."
            />
          ) : (
            <div className="space-y-4">
              {awards.map((award) => (
                <Card key={award.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-gray-500">{award.tender_id ?? ''}</span>
                        <h3 className="text-sm font-medium text-gray-900 dark:text-white">{award.work_name}</h3>
                      </div>
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{award.procuring_entity} · {award.contractor_name}</p>
                    </div>
                    <Badge tone={award.discount_pct !== undefined && award.discount_pct < 0 ? 'success' : award.discount_pct !== undefined && award.discount_pct > 0 ? 'warning' : 'default'}>
                      {award.discount_pct !== undefined ? (award.discount_pct > 0 ? 'Above' : 'Below') : 'N/A'}
                    </Badge>
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
                      <span className="text-gray-500">Estimated</span>
                      <p className="font-medium text-gray-900 dark:text-white">৳{((award.estimated_cost ?? 0) / 1e7).toFixed(1)}Cr</p>
                    </div>
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
                      <span className="text-gray-500">Awarded</span>
                      <p className="font-medium text-gray-900 dark:text-white">৳{((award.awarded_amount ?? 0) / 1e7).toFixed(1)}Cr</p>
                    </div>
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/60">
                      <span className="text-gray-500">Variance</span>
                      <p className={cn(
                        'font-medium',
                        award.discount_pct !== undefined && award.discount_pct < 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                      )}>
                        {award.discount_pct !== undefined ? (award.discount_pct > 0 ? '+' : '') + award.discount_pct.toFixed(1) + '%' : 'N/A'}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                    <Award className="h-3 w-3" />
                    Awarded: {award.award_date ? new Date(award.award_date).toLocaleDateString() : 'N/A'}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      }
    />
  )
}
