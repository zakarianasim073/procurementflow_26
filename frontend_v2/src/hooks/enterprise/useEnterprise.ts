import { useQuery } from '@tanstack/react-query'
import { getCapabilities, getAuditLogs, getTenantInfo, getTeamMembers, getRoles } from '@entities/index'

export function useCapabilities() {
  return useQuery({
    queryKey: ['enterprise', 'capabilities'],
    queryFn: () => getCapabilities(),
    staleTime: 300_000,
  })
}

export function useAuditLogs(limit = 50) {
  return useQuery({
    queryKey: ['enterprise', 'audit-logs', limit],
    queryFn: () => getAuditLogs(limit),
    staleTime: 60_000,
  })
}

export function useTenantInfo() {
  return useQuery({
    queryKey: ['enterprise', 'tenant'],
    queryFn: () => getTenantInfo(),
    staleTime: 60_000,
  })
}

export function useTeamMembers() {
  return useQuery({
    queryKey: ['enterprise', 'team'],
    queryFn: () => getTeamMembers(),
    staleTime: 60_000,
  })
}

export function useRoles() {
  return useQuery({
    queryKey: ['enterprise', 'roles'],
    queryFn: () => getRoles(),
    staleTime: 60_000,
  })
}
