import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import { useSorSearch, useSorAgencies, useSorCompare } from './useSor'

vi.mock('@entities/sor', () => ({
  searchSor: vi.fn(),
  getSorAgencies: vi.fn(),
  compareSor: vi.fn(),
  lookupSor: vi.fn(),
}))

import { searchSor, getSorAgencies, compareSor } from '@entities/sor'

const mockedSearchSor = vi.mocked(searchSor)
const mockedGetSorAgencies = vi.mocked(getSorAgencies)
const mockedCompareSor = vi.mocked(compareSor)

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useSorSearch', () => {
  beforeEach(() => vi.clearAllMocks())

  it('searches when query is provided', async () => {
    mockedSearchSor.mockResolvedValue([{ code: '40-200-00', description: 'Earthwork' }] as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useSorSearch('earthwork'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedSearchSor).toHaveBeenCalledWith('earthwork', undefined)
  })

  it('does not search when query is empty', () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useSorSearch(''), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useSorAgencies', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches agencies list', async () => {
    mockedGetSorAgencies.mockResolvedValue({ agencies: ['BWDB', 'PWD', 'LGED'], total_rates: 4545 } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useSorAgencies(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.agencies).toEqual(['BWDB', 'PWD', 'LGED'])
  })
})

describe('useSorCompare', () => {
  beforeEach(() => vi.clearAllMocks())

  it('compares codes across agencies', async () => {
    mockedCompareSor.mockResolvedValue([] as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useSorCompare(['40-200-00'], ['BWDB', 'PWD']), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedCompareSor).toHaveBeenCalledWith(['40-200-00'], ['BWDB', 'PWD'])
  })

  it('does not compare when codes are empty', () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useSorCompare([], ['BWDB']), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
  })
})
