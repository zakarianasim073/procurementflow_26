import type { RuleGraph, RuleRelationship, RuleCluster } from './types'
import { fetchJson } from '@entities/sharedApi'

const BASE = '/api/v2'

export function getRuleGraph(): Promise<RuleGraph> {
  return fetchJson<RuleGraph>(`${BASE}/rule-graph`, true)
}

export function getRelationship(source: string, target: string): Promise<RuleRelationship> {
  return fetchJson<RuleRelationship>(`${BASE}/rule-graph/relationships?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`, true)
}

export function getRuleClusters(): Promise<RuleCluster[]> {
  return fetchJson<RuleCluster[]>(`${BASE}/rule-clusters`, true)
}
