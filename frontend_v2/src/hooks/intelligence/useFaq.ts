import { useQuery } from '@tanstack/react-query'
import { getFaq } from '@entities/index'

export function useFaq() {
  return useQuery({
    queryKey: ['intelligence', 'faq'],
    queryFn: getFaq,
    staleTime: 600_000,
    retry: 1,
  })
}
