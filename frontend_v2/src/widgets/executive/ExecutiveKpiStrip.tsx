import { Briefcase, TrendingUp, Activity, Building2 } from 'lucide-react'
import type { ExecutivePipeline, ExecutiveOverview } from '@entities/executive/types'
import { KpiCard } from './KpiCard'

interface ExecutiveKpiStripProps {
  pipeline: ExecutivePipeline | undefined
  overview: ExecutiveOverview | undefined
  isLoading: boolean
}

function formatBdt(value: number): string {
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`
  if (value >= 1e7) return `${(value / 1e7).toFixed(1)}Cr`
  if (value >= 1e5) return `${(value / 1e5).toFixed(1)}L`
  return value.toLocaleString()
}

function calcDelta(current: number, prev: number): { value: string; direction: 'up' | 'down' | 'neutral' } {
  if (prev === 0) return { value: 'N/A', direction: 'neutral' }
  const pct = ((current - prev) / prev) * 100
  const sign = pct > 0 ? '+' : ''
  return {
    value: `${sign}${pct.toFixed(1)}%`,
    direction: pct > 0 ? 'up' : pct < 0 ? 'down' : 'neutral',
  }
}

export function ExecutiveKpiStrip({ pipeline, overview, isLoading }: ExecutiveKpiStripProps) {
  const liveTenders = pipeline?.total_live_tenders ?? 0
  const pipelineValue = pipeline?.estimated_total_pipeline_value_bdt ?? 0
  const eexperienceValue = overview?.execution.eexperience_value_bdt ?? 0
  const ecmsValue = overview?.execution.ecms_value_bdt ?? 0
  const totalRevenue = eexperienceValue + ecmsValue
  const activeAgents = overview?.agents.active ?? 0
  const totalAgents = overview?.agents.total ?? 0
  const knowledgeTotal = overview?.embedding.knowledge_total ?? 0

  // Synthetic sparkline data from agency breakdown
  const pipelineSpark = (pipeline?.agencies ?? []).map(a => a.live_tenders)
  const revenueSpark = [
    overview?.execution.eexperience_completed ?? 0,
    overview?.execution.ecms_ongoing ?? 0,
  ]

  const agentHealthPct = totalAgents > 0 ? Math.round((activeAgents / totalAgents) * 100) : 0
  const healthSpark = [
    agentHealthPct,
    Math.min(100, agentHealthPct + 5),
    Math.max(0, agentHealthPct - 3),
    agentHealthPct,
  ]

  return (
    <>
      <KpiCard
        label="Revenue (E+ECMS)"
        value={`${formatBdt(totalRevenue)}`}
        delta={calcDelta(eexperienceValue, ecmsValue)}
        icon={<Briefcase className="h-4 w-4" />}
        sparkData={revenueSpark}
        sparkColor="#10b981"
        isLoading={isLoading}
      />
      <KpiCard
        label="Pipeline Value"
        value={`${formatBdt(pipelineValue)}`}
        delta={{ value: `${liveTenders} live`, direction: liveTenders > 0 ? 'up' : 'neutral' }}
        icon={<TrendingUp className="h-4 w-4" />}
        sparkData={pipelineSpark}
        sparkColor="#4f46e5"
        isLoading={isLoading}
      />
      <KpiCard
        label="Company Health"
        value={`${agentHealthPct}%`}
        delta={{ value: `${activeAgents}/${totalAgents} agents`, direction: agentHealthPct > 80 ? 'up' : 'down' }}
        icon={<Building2 className="h-4 w-4" />}
        sparkData={healthSpark}
        sparkColor="#8b5cf6"
        isLoading={isLoading}
      />
      <KpiCard
        label="Knowledge Base"
        value={knowledgeTotal.toLocaleString()}
        delta={{ value: 'entries', direction: 'neutral' }}
        icon={<Activity className="h-4 w-4" />}
        isLoading={isLoading}
      />
    </>
  )
}
