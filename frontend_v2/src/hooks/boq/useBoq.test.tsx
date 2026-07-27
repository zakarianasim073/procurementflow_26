import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import { useBoqUpload, useBoqCompare, useBoqBrainCompare, useBoqJobStatus, useBoqHistory } from './useBoq'

vi.mock('@entities/boq', () => ({
  uploadBoq: vi.fn(),
  compareBoq: vi.fn(),
  brainCompare: vi.fn(),
  getBoqJobStatus: vi.fn(),
  getBoqJobResult: vi.fn(),
  getBoqLatest: vi.fn(),
  getBoqHistory: vi.fn(),
}))

import { uploadBoq, compareBoq, brainCompare, getBoqJobStatus, getBoqHistory } from '@entities/boq'

const mockedUploadBoq = vi.mocked(uploadBoq)
const mockedCompareBoq = vi.mocked(compareBoq)
const mockedBrainCompare = vi.mocked(brainCompare)
const mockedGetBoqJobStatus = vi.mocked(getBoqJobStatus)
const mockedGetBoqHistory = vi.mocked(getBoqHistory)

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useBoqUpload', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls uploadBoq with file', async () => {
    mockedUploadBoq.mockResolvedValue({ job_id: 'j1', status: 'pending' } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useBoqUpload(), { wrapper })

    const file = new File(['test'], 'boq.pdf', { type: 'application/pdf' })
    result.current.mutate({ file })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedUploadBoq).toHaveBeenCalledWith(file)
  })
})

describe('useBoqCompare', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls compareBoq with params', async () => {
    mockedCompareBoq.mockResolvedValue({ job_id: 'j2', status: 'pending' } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useBoqCompare(), { wrapper })

    result.current.mutate({ boqFileId: 'f1', sorAgency: 'BWDB', zone: 'A' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedCompareBoq).toHaveBeenCalledWith('f1', 'BWDB', 'A', undefined)
  })
})

describe('useBoqBrainCompare', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls brainCompare with tender info', async () => {
    mockedBrainCompare.mockResolvedValue({ job_id: 'j3', status: 'pending' } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useBoqBrainCompare(), { wrapper })

    result.current.mutate({ tenderId: '1298004', sorAgency: 'BWDB', zone: 'A' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedBrainCompare).toHaveBeenCalledWith('1298004', 'BWDB', 'A')
  })
})

describe('useBoqJobStatus', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches job status when jobId provided', async () => {
    mockedGetBoqJobStatus.mockResolvedValue({ status: 'completed' } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useBoqJobStatus('j1'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('completed')
  })

  it('does not fetch when jobId is empty', () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useBoqJobStatus(''), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useBoqHistory', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches history with pagination', async () => {
    mockedGetBoqHistory.mockResolvedValue([{ id: '1' }] as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useBoqHistory(0, 10), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedGetBoqHistory).toHaveBeenCalledWith(0, 10)
  })
})
