import { useQuery } from '@tanstack/react-query'
import { getPredictionsModelStatus } from '@entities/index'

export function usePredictionsModelStatus() {
  return useQuery({
    queryKey: ['predictions', 'model-status'],
    queryFn: getPredictionsModelStatus,
    staleTime: 5 * 60_000,
    retry: 2,
  })
}
