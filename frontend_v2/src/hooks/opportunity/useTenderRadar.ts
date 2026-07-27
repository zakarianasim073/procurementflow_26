import { useQuery } from '@tanstack/react-query'
import { getTenderRadar } from '@entities/index'

export function useTenderRadar() {
  return useQuery({
    queryKey: ['opportunity', 'tender-radar'],
    queryFn: getTenderRadar,
    staleTime: 30_000,
    retry: 1,
  })
}
