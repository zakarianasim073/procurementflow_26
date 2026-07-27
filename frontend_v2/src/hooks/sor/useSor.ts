import { useQuery } from '@tanstack/react-query'
import { searchSor, getSorAgencies, compareSor } from '@entities/sor'

export function useSorSearch(query: string, agency?: string) {
  return useQuery({
    queryKey: ['sor', 'search', query, agency],
    queryFn: () => searchSor(query, agency),
    staleTime: 60_000,
    enabled: !!query,
  })
}

export function useSorAgencies() {
  return useQuery({
    queryKey: ['sor', 'agencies'],
    queryFn: () => getSorAgencies(),
    staleTime: 300_000,
  })
}

export function useSorCompare(codes: string[], agencies: string[]) {
  return useQuery({
    queryKey: ['sor', 'compare', codes, agencies],
    queryFn: () => compareSor(codes, agencies),
    staleTime: 60_000,
    enabled: codes.length > 0 && agencies.length > 0,
  })
}
