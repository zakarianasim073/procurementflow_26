import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
} from '@entities/index'
import { getRegisteredAgents, getBrainStatus, getRecentAgentRuns, getPipelinePhases, runAgent } from '@entities/index'

export const useRegisteredAgents = () => {
  return useQuery({
    queryKey: ['registeredAgents'],
    queryFn: getRegisteredAgents,
  })
}

export const useBrainStatus = () => {
  return useQuery({
    queryKey: ['brainStatus'],
    queryFn: getBrainStatus,
  })
}

export const useRecentAgentRuns = (limit = 50) => {
  return useQuery({
    queryKey: ['recentAgentRuns', limit],
    queryFn: () => getRecentAgentRuns(limit),
  })
}

export const usePipelinePhases = () => {
  return useQuery({
    queryKey: ['pipelinePhases'],
    queryFn: getPipelinePhases,
  })
}

export const useRunAgent = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (params: { agentId: string; input?: Record<string, unknown> }) =>
      runAgent(params.agentId, params.input ?? {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recentAgentRuns'] })
      queryClient.invalidateQueries({ queryKey: ['brainStatus'] })
    },
  })
}

export const useAgents = () => {
  const registeredAgentsQuery = useRegisteredAgents()
  const brainStatusQuery = useBrainStatus()
  const recentAgentRunsQuery = useRecentAgentRuns()
  const pipelinePhasesQuery = usePipelinePhases()
  const runAgentMutation = useRunAgent()

  return {
    registeredAgents: registeredAgentsQuery.data ?? [],
    isRegisteredAgentsLoading: registeredAgentsQuery.isLoading,
    brainStatus: brainStatusQuery.data,
    isBrainStatusLoading: brainStatusQuery.isLoading,
    recentAgentRuns: recentAgentRunsQuery.data ?? [],
    isRecentAgentRunsLoading: recentAgentRunsQuery.isLoading,
    pipelinePhases: pipelinePhasesQuery.data ?? [],
    isPipelinePhasesLoading: pipelinePhasesQuery.isLoading,
    runAgent: runAgentMutation.mutateAsync,
    isRunningAgent: runAgentMutation.isPending,
  }
}