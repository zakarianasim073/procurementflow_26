import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import { useComplianceCheck, useTdsCriteria, useRunComplianceCheck } from './useCompliance'

vi.mock('@entities/compliance', () => ({
  getComplianceCheck: vi.fn(),
  getTdsCriteria: vi.fn(),
  runComplianceCheck: vi.fn(),
}))

import { getComplianceCheck, getTdsCriteria, runComplianceCheck } from '@entities/compliance'

const mockedGetComplianceCheck = vi.mocked(getComplianceCheck)
const mockedGetTdsCriteria = vi.mocked(getTdsCriteria)
const mockedRunComplianceCheck = vi.mocked(runComplianceCheck)

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useComplianceCheck', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches compliance data for a tender', async () => {
    mockedGetComplianceCheck.mockResolvedValue({ tender_id: 'T001', checks: [] } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useComplianceCheck('T001'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedGetComplianceCheck).toHaveBeenCalledWith('T001')
  })

  it('does not fetch without tenderId', () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useComplianceCheck(''), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useTdsCriteria', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches TDS criteria', async () => {
    mockedGetTdsCriteria.mockResolvedValue({ criteria: [] } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useTdsCriteria('T001'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedGetTdsCriteria).toHaveBeenCalledWith('T001')
  })
})

describe('useRunComplianceCheck', () => {
  beforeEach(() => vi.clearAllMocks())

  it('triggers compliance check mutation', async () => {
    mockedRunComplianceCheck.mockResolvedValue({ status: 'ok' } as any)
    const wrapper = createWrapper()
    const { result } = renderHook(() => useRunComplianceCheck(), { wrapper })

    result.current.mutate('T001')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedRunComplianceCheck).toHaveBeenCalledWith('T001')
  })
})
