import { useQuery } from '@tanstack/react-query'
import { getContractorCapacity, getContractorFinance, getTenderRecommendation, getTenderTDSCriteria } from '@entities/index'

export function useContractorCapacity(contractorId: string, tenderValueBdt?: number) {
  return useQuery({
    queryKey: ['qualification', 'capacity', contractorId, tenderValueBdt],
    queryFn: () => getContractorCapacity(contractorId, tenderValueBdt),
    staleTime: 60_000,
    enabled: !!contractorId,
  })
}

export function useContractorFinance(contractorId: string) {
  return useQuery({
    queryKey: ['qualification', 'finance', contractorId],
    queryFn: () => getContractorFinance(contractorId),
    staleTime: 60_000,
    enabled: !!contractorId,
  })
}

export function useTenderRecommendation(tenderId: string, contractorId: string) {
  return useQuery({
    queryKey: ['qualification', 'recommendation', tenderId, contractorId],
    queryFn: () => getTenderRecommendation(tenderId, contractorId),
    staleTime: 60_000,
    enabled: !!tenderId && !!contractorId,
  })
}

export function useTenderTDSCriteria(tenderId: string) {
  return useQuery({
    queryKey: ['qualification', 'tds', tenderId],
    queryFn: () => getTenderTDSCriteria(tenderId),
    staleTime: 120_000,
    enabled: !!tenderId,
  })
}
