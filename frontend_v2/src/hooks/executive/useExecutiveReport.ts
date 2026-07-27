import { useQuery } from '@tanstack/react-query'
import { getExecutiveReport } from '@entities/index'

export function useExecutiveReport() {
  return useQuery({
    queryKey: ['executive', 'report'],
    queryFn: getExecutiveReport,
    staleTime: 5 * 60_000,
    retry: 2,
  })
}
