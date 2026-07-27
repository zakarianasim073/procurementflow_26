import { useQuery } from '@tanstack/react-query'
import { getExecutivePipeline } from '@entities/index'

export function useExecutivePipeline() {
  return useQuery({
    queryKey: ['executive', 'pipeline'],
    queryFn: getExecutivePipeline,
    staleTime: 60_000,
    retry: 2,
  })
}
