import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import { useCompetitors, useCompetitorAnalysis } from './useCompetitor'

vi.mock('@entities/competitor', () => ({
  getCompetitors: vi.fn(),
  getCompetitorAnalysis: vi.fn(),
}))

import { getCompetitors, getCompetitorAnalysis } from '@entities/competitor'

const mockedGetCompetitors = vi.mocked(getCompetitors)
const mockedGetCompetitorAnalysis = vi.mocked(getCompetitorAnalysis)

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useCompetitors', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches competitors for a tender', async () => {
    mockedGetCompetitors.mockResolvedValue([{ contractor_name: 'ABC Ltd' }] as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useCompetitors({ search: 'T001' }), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedGetCompetitors).toHaveBeenCalledWith({ search: 'T001' })
  })

  it('fetches all competitors when no tenderId', async () => {
    mockedGetCompetitors.mockResolvedValue([] as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useCompetitors(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedGetCompetitors).toHaveBeenCalledWith(undefined)
  })
})

describe('useCompetitorAnalysis', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches analysis for a tender', async () => {
    mockedGetCompetitorAnalysis.mockResolvedValue({ competitors: [], summary: 'ok' } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useCompetitorAnalysis('T001'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedGetCompetitorAnalysis).toHaveBeenCalledWith('T001')
  })

  it('does not fetch without tenderId', () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useCompetitorAnalysis(''), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
  })
})
