import { useQuery } from '@tanstack/react-query'
import { searchKnowledge } from '@entities/index'

export function useKnowledgeSearch(query: string) {
  return useQuery({
    queryKey: ['intelligence', 'knowledge-search', query],
    queryFn: () => searchKnowledge(query),
    enabled: query.length >= 2,
    staleTime: 120_000,
    retry: 1,
  })
}
