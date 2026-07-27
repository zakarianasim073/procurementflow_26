import type { ClauseTreeNode, ClauseTag } from './types'
import { fetchJson } from '@entities/sharedApi'

const BASE = '/api/v2/clauses'

export function getClauseTree(): Promise<ClauseTreeNode> {
  return fetchJson<ClauseTreeNode>(`${BASE}/tree`, true)
}

export function getClauseTags(): Promise<ClauseTag[]> {
  return fetchJson<ClauseTag[]>(`${BASE}/tags`, true)
}
