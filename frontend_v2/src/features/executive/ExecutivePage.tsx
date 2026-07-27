import { useNavigate } from 'react-router-dom'
import { BarChart3, TrendingUp } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { useExecutivePipeline, useExecutiveOverview } from '@hooks/index'
import {
  ExecutiveKpiStrip,
  PipelineFunnelBarChart,
  PipelineSummary,
  ExecutionSummary,
  UrgentActionsPanel,
  AiSummary,
  MarketIntelligence,
} from '@widgets/executive/index'

export function ExecutivePage() {
  const navigate = useNavigate()
  const pipeline = useExecutivePipeline()
  const overview = useExecutiveOverview()

  const isLoading = pipeline.isLoading || overview.isLoading

  // Real urgent-action strings derived from agencies with tenders closing within 7 days
  const urgentActions = (pipeline.data?.agencies ?? [])
    .filter((a) => a.closing_7d > 0)
    .sort((a, b) => b.closing_7d - a.closing_7d)
    .slice(0, 5)
    .map((a) => `${a.agency_code}: ${a.closing_7d} tender${a.closing_7d !== 1 ? 's' : ''} closing within 7 days`)

  // Top agencies by pipeline value (real data)
  const topAgencies = [...(pipeline.data?.agencies ?? [])]
    .sort((a, b) => b.estimated_pipeline_value_bdt - a.estimated_pipeline_value_bdt)
    .slice(0, 8)

  // Navigate to pipeline details on card click
  const handlePipelineClick = () => {
    navigate('/executive/pipeline')
  }

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Executive Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Real-time procurement intelligence across your organization
          </p>
        </div>
      }
      kpiStrip={
        isLoading ? (
          <div className="flex gap-3 overflow-x-auto pb-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-56 shrink-0 rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-2">
            <ExecutiveKpiStrip
              pipeline={pipeline.data}
              overview={overview.data}
              isLoading={isLoading}
            />
          </div>
        )
      }
      primary={
        <div className="space-y-6">
          {/* Pipeline Summary Card */}
          {isLoading ? (
            <Skeleton className="h-80 w-full rounded-xl" />
          ) : pipeline.data ? (
            <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-blue-600" />
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Pipeline Overview</h2>
                </div>
                <button
                  onClick={handlePipelineClick}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700 dark:hover:text-blue-400"
                >
                  View Details →
                </button>
              </div>
              <PipelineFunnelBarChart data={pipeline.data} />
            </div>
          ) : null}

          {/* Two-column grid for summaries */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Pipeline Summary */}
            {isLoading ? (
              <Skeleton className="h-64 w-full rounded-xl" />
            ) : pipeline.data ? (
              <PipelineSummary data={pipeline.data} />
            ) : null}

            {/* Execution Summary */}
            {isLoading ? (
              <Skeleton className="h-64 w-full rounded-xl" />
            ) : overview.data ? (
              <ExecutionSummary
                eexperienceCompleted={overview.data.execution.eexperience_completed}
                ecmsOngoing={overview.data.execution.ecms_ongoing}
                eexperienceValueBdt={overview.data.execution.eexperience_value_bdt}
                ecmsValueBdt={overview.data.execution.ecms_value_bdt}
              />
            ) : null}
          </div>

          {/* Market Intelligence — self-contained widget (fetches its own data) */}
          {isLoading ? (
            <Skeleton className="h-64 w-full rounded-xl" />
          ) : (
            <MarketIntelligence />
          )}

          {/* AI Summary — self-contained widget */}
          {isLoading ? (
            <Skeleton className="h-48 w-full rounded-xl" />
          ) : (
            <AiSummary />
          )}
        </div>
      }
      aiDock={
        <UrgentActionsPanel
          liveTenders={pipeline.data?.total_live_tenders ?? 0}
          actionItems={urgentActions}
          isLoading={isLoading}
        />
      }
      activityTimeline={
        isLoading ? (
          <Skeleton className="h-64 w-full rounded-xl" />
        ) : pipeline.data && pipeline.data.agencies.length > 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
              <TrendingUp className="h-4 w-4" /> Top Agencies by Pipeline
            </h3>
            <div className="space-y-2">
              {topAgencies.map((a) => (
                <div key={a.agency_code} className="flex items-center justify-between text-xs">
                  <span className="font-medium text-gray-700 dark:text-gray-300">{a.agency_code}</span>
                  <div className="flex items-center gap-3 text-gray-500">
                    <span className="tabular-nums">{a.live_tenders} live</span>
                    <span className="tabular-nums">{(a.estimated_pipeline_value_bdt / 1e7).toFixed(1)}Cr</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null
      }
    />
  )
}
