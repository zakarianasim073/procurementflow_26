import { useQuery } from '@tanstack/react-query'
import { getAuditLogs } from '@entities/admin'

export function useAuditLogs(skip: number = 0, limit: number = 50) {
  return useQuery({
    queryKey: ['admin', 'audit-logs', skip, limit],
    queryFn: () => getAuditLogs(skip, limit),
    staleTime: 30_000,
    retry: 1,
  })
}
