import { useQuery } from '@tanstack/react-query'
import { getClauseTags } from '@entities/index'

export function useClauseTags() {
  return useQuery({
    queryKey: ['clauseTags'],
    queryFn: () => getClauseTags(),
    staleTime: 300_000,
    retry: 1,
  })
}
