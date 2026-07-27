import { useQuery } from '@tanstack/react-query'
import {
  getMarketOverview,
  getAwardHistory,
  getAgencyBehaviour,
  getTopContractors,
  getNppiAnalysis,
} from '@entities/marketIntel'

const STALE = 5 * 60_000

export function useMarketOverview() {
  return useQuery({
    queryKey: ['marketIntel', 'overview'],
    queryFn: getMarketOverview,
    staleTime: STALE,
  })
}

export function useAwardHistory(years = 8, agency?: string) {
  return useQuery({
    queryKey: ['marketIntel', 'awardHistory', years, agency],
    queryFn: () => getAwardHistory(years, agency),
    staleTime: STALE,
  })
}

export function useAgencyBehaviour(limit = 15) {
  return useQuery({
    queryKey: ['marketIntel', 'agencies', limit],
    queryFn: () => getAgencyBehaviour(limit),
    staleTime: STALE,
  })
}

export function useTopContractors(limit = 20, agency?: string) {
  return useQuery({
    queryKey: ['marketIntel', 'contractors', limit, agency],
    queryFn: () => getTopContractors(limit, agency),
    staleTime: STALE,
  })
}

export function useNppiAnalysis() {
  return useQuery({
    queryKey: ['marketIntel', 'nppi'],
    queryFn: getNppiAnalysis,
    staleTime: STALE,
  })
}
