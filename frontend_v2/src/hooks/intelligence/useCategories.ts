import { useQuery } from '@tanstack/react-query'
import { getCategories } from '@entities/intelligence'
import type { CategoryItem } from '@entities/intelligence'

export function useCategories() {
  return useQuery<CategoryItem[]>({
    queryKey: ['categories'],
    queryFn: getCategories,
    staleTime: 600_000,
    retry: 1,
  })
}