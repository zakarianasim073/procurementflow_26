import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import { useAwards, useAwardStats } from './useAward'

vi.mock('@entities/award', () => ({
  getAwards: vi.fn(),
  getAwardStats: vi.fn(),
}))

import { getAwards, getAwardStats } from '@entities/award'

const mockedGetAwards = vi.mocked(getAwards)
const mockedGetAwardStats = vi.mocked(getAwardStats)

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useAwards', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches awards for a tender', async () => {
    mockedGetAwards.mockResolvedValue([{ package_no: 'P001' }] as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useAwards({ procuring_entity: 'P001' }), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedGetAwards).toHaveBeenCalledWith({ procuring_entity: 'P001' })
  })

  it('fetches all awards when no tenderId', async () => {
    mockedGetAwards.mockResolvedValue([] as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useAwards(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedGetAwards).toHaveBeenCalledWith(undefined)
  })
})

describe('useAwardStats', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches award statistics', async () => {
    mockedGetAwardStats.mockResolvedValue({ total_awards: 238000, total_value: 1e12 } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useAwardStats(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedGetAwardStats).toHaveBeenCalled()
  })
})
