import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getComplianceCheck, getTdsCriteria, runComplianceCheck } from '@entities/compliance'

export function useComplianceCheck(tenderId: string) {
  return useQuery({
    queryKey: ['compliance', tenderId],
    queryFn: () => getComplianceCheck(tenderId),
    staleTime: 60_000,
    enabled: !!tenderId,
  })
}

export function useTdsCriteria(tenderId: string) {
  return useQuery({
    queryKey: ['tds', tenderId],
    queryFn: () => getTdsCriteria(tenderId),
    staleTime: 60_000,
    enabled: !!tenderId,
  })
}

export function useRunComplianceCheck() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (tenderId: string) => runComplianceCheck(tenderId),
    onSuccess: (_, tenderId) => {
      queryClient.invalidateQueries({ queryKey: ['compliance', tenderId] })
    },
  })
}
