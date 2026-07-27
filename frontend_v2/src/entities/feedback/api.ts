import type { FeedbackEntry, FeedbackSubmitPayload, FeedbackStats, FeedbackAwaitingItem, FeedbackSubmitResult } from './types'
import { fetchJson } from '@entities/sharedApi'

const BASE = '/api/v2/feedback'

export async function submitFeedback(data: FeedbackSubmitPayload): Promise<FeedbackSubmitResult> {
  return fetchJson<FeedbackSubmitResult>(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    authed: true,
  })
}

export async function getFeedbackForTender(tenderId: string): Promise<FeedbackEntry | null> {
  try {
    return await fetchJson<FeedbackEntry>(`${BASE}/${tenderId}`, true)
  } catch {
    return null
  }
}

export async function getFeedbackStats(): Promise<FeedbackStats> {
  return fetchJson<FeedbackStats>(`${BASE}/stats`, true)
}

export async function getFeedbackAwaiting(): Promise<FeedbackAwaitingItem[]> {
  return fetchJson<FeedbackAwaitingItem[]>(`${BASE}/awaiting`, true)
}
