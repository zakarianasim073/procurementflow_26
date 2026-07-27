import { useQuery } from '@tanstack/react-query'
import { getExecutiveRoi } from '@entities/roi/api'

export function useExecutiveRoi(params?: { period?: string; start?: string; end?: string }) {
  return useQuery({
    queryKey: ['executiveRoi', params],
    queryFn: () => getExecutiveRoi(params),
    staleTime: 120_000,
  })
}
