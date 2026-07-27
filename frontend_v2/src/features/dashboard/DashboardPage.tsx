import { ScreenTemplate, KpiStrip, AiDockSlot, TrustPanelSlot, ActivityTimelineSlot } from '@layouts/index'
import { useExecutiveOverview, useExecutivePipeline, useExecutiveReport } from '@hooks/index'
import { ExecutiveKpiStrip, PipelineSummary, PipelineSummarySkeleton, ExecutionSummary, ExecutionSummarySkeleton, AiSummary, PipelineFunnelBarChart, UrgentActionsPanel, MarketIntelligence } from '@widgets/index'

export function DashboardPage() {
  const overview = useExecutiveOverview()
  const pipeline = useExecutivePipeline()
  const report = useExecutiveReport()

  const isLoading = overview.isLoading || pipeline.isLoading
  const error = overview.error || pipeline.error

  const execData = overview.data
  const pipeData = pipeline.data
  const reportData = report.data

  return (
    <ScreenTemplate
      header={
        <>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Executive Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {execData?.timestamp
              ? `Last updated ${new Date(execData.timestamp).toLocaleString()}`
              : 'ProcureFlow tender intelligence overview'}
          </p>
        </>
      }
      kpiStrip={
        <KpiStrip>
          {error ? (
            <KpiErrorCard message="Couldn't load this right now. Retry." />
          ) : (
            <ExecutiveKpiStrip
              pipeline={pipeData}
              overview={execData}
              isLoading={isLoading}
            />
          )}
        </KpiStrip>
      }
      primary={
        <>
          {error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
              Couldn't load dashboard data. <button onClick={() => { overview.refetch(); pipeline.refetch(); }} className="underline font-medium">Retry.</button>
            </div>
          ) : pipeData ? (
            <PipelineSummary data={pipeData} />
          ) : pipeline.isLoading ? (
            <PipelineSummarySkeleton />
          ) : null}

          {pipeData ? (
            <PipelineFunnelBarChart data={pipeData} isLoading={pipeline.isLoading} />
          ) : null}

          {execData ? (
            <ExecutionSummary
              eexperienceCompleted={execData.execution.eexperience_completed}
              ecmsOngoing={execData.execution.ecms_ongoing}
              eexperienceValueBdt={execData.execution.eexperience_value_bdt}
              ecmsValueBdt={execData.execution.ecms_value_bdt}
            />
          ) : overview.isLoading ? (
            <ExecutionSummarySkeleton />
          ) : null}

          {reportData ? (
            <UrgentActionsPanel
              actionItems={reportData.report?.procurement_head_decision?.action_items}
              liveTenders={pipeData?.total_live_tenders}
              isLoading={report.isLoading}
            />
          ) : null}

          {execData && execData.pipeline.total_agents_phased > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
              <h2 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Agent Pipeline</h2>
              <div className="space-y-2">
                {execData.pipeline.phases.map((phase) => (
                  <div key={phase.phase} className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">{phase.label}</span>
                    <span className="font-medium tabular-nums text-gray-900 dark:text-white">
                      {phase.registered}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      }
      aiDock={
        <AiDockSlot>
          <MarketIntelligence />
        </AiDockSlot>
      }
      trustPanel={
        <TrustPanelSlot>
          <AiSummary />
        </TrustPanelSlot>
      }
      activityTimeline={
        execData ? (
          <ActivityTimelineSlot>
            <ul className="space-y-2">
              <li className="text-sm text-gray-600 dark:text-gray-400">
                {execData.execution.eexperience_completed.toLocaleString()} completed experiences tracked
              </li>
              <li className="text-sm text-gray-600 dark:text-gray-400">
                {execData.execution.ecms_ongoing.toLocaleString()} ongoing contracts monitored
              </li>
              <li className="text-sm text-gray-600 dark:text-gray-400">
                {execData.agents.active} of {execData.agents.total} agents active
              </li>
              <li className="text-sm text-gray-600 dark:text-gray-400">
                {execData.embedding.knowledge_total.toLocaleString()} knowledge entries indexed
              </li>
            </ul>
          </ActivityTimelineSlot>
        ) : (
          <ActivityTimelineSlot>
            <ul className="space-y-2">
              <li className="text-sm text-gray-400">Activity data loads with live API.</li>
            </ul>
          </ActivityTimelineSlot>
        )
      }
    />
  )
}

function KpiErrorCard({ message }: { message: string }) {
  return (
    <div className="flex w-56 shrink-0 items-center rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
      {message}
    </div>
  )
}
