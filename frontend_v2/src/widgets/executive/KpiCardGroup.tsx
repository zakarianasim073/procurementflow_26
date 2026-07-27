import { KpiCard } from './KpiCard'

interface KpiCardGroupProps {
  totalLiveTenders: number
  estimatedPipelineValueBdt: number
  totalPredictions: number
  nppRecords: number
  isLoading: boolean
}

export function KpiCardGroup({
  totalLiveTenders,
  estimatedPipelineValueBdt,
  totalPredictions,
  nppRecords,
  isLoading,
}: KpiCardGroupProps) {
  return (
    <>
      <KpiCard
        label="Live Tenders"
        value={totalLiveTenders.toLocaleString()}
        isLoading={isLoading}
      />
      <KpiCard
        label="Pipeline Value"
        value={`${(estimatedPipelineValueBdt / 1e7).toFixed(1)}Cr`}
        isLoading={isLoading}
      />
      <KpiCard
        label="AI Forecasts"
        value={totalPredictions.toLocaleString()}
        isLoading={isLoading}
      />
      <KpiCard
        label="NPP Records"
        value={nppRecords.toLocaleString()}
        isLoading={isLoading}
      />
    </>
  )
}
