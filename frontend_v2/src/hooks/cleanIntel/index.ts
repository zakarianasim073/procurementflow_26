import { useQuery } from '@tanstack/react-query'
import { getCatalogue, getDataset } from '@entities/cleanIntel'

const STALE = 5 * 60_000

export function useIntelCatalogue() {
  return useQuery({ queryKey: ['cleanIntel', 'catalogue'], queryFn: getCatalogue, staleTime: STALE })
}

export function useIntelDataset(dataset: string, limit = 50, offset = 0, q?: string) {
  return useQuery({
    queryKey: ['cleanIntel', dataset, limit, offset, q],
    queryFn: () => getDataset(dataset, limit, offset, q),
    staleTime: STALE,
    enabled: !!dataset,
  })
}
