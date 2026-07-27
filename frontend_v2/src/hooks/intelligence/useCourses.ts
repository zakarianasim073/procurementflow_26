import { useQuery } from '@tanstack/react-query'
import { getCourses } from '@entities/index'

export function useCourses() {
  return useQuery({
    queryKey: ['intelligence', 'courses'],
    queryFn: getCourses,
    staleTime: 600_000,
    retry: 1,
  })
}
