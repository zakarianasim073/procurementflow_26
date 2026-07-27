import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadBoq, compareBoq, brainCompare, getBoqJobStatus, getBoqJobResult, getBoqLatest, getBoqHistory } from '@entities/boq'

export function useBoqResult(tenderId: string) {
  return useQuery({
    queryKey: ['boq', 'result', tenderId],
    queryFn: () => getBoqLatest(),
    staleTime: 60_000,
    enabled: !!tenderId,
  })
}

export function useBoqUpload() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file }: { file: File }) => uploadBoq(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['boq'] })
    },
  })
}

export function useBoqCompare() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ boqFileId, sorAgency, zone, tenderInfo }: { boqFileId: string; sorAgency: string; zone?: string; tenderInfo?: string }) =>
      compareBoq(boqFileId, sorAgency, zone, tenderInfo),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['boq'] })
    },
  })
}

export function useBoqBrainCompare() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ tenderId, sorAgency, zone }: { tenderId: string; sorAgency: string; zone?: string }) =>
      brainCompare(tenderId, sorAgency, zone),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['boq'] })
    },
  })
}

export function useBoqJobStatus(jobId: string) {
  return useQuery({
    queryKey: ['boq', 'job', jobId],
    queryFn: () => getBoqJobStatus(jobId),
    staleTime: 5_000,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'completed' || status === 'failed') return false
      return 3_000
    },
    enabled: !!jobId,
  })
}

export function useBoqJobResult(jobId: string) {
  return useQuery({
    queryKey: ['boq', 'job', jobId, 'result'],
    queryFn: () => getBoqJobResult(jobId),
    staleTime: 60_000,
    enabled: !!jobId,
  })
}

export function useBoqHistory(skip = 0, limit = 20) {
  return useQuery({
    queryKey: ['boq', 'history', skip, limit],
    queryFn: () => getBoqHistory(skip, limit),
    staleTime: 60_000,
  })
}
