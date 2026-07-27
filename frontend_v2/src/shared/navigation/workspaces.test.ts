import { describe, expect, it } from 'vitest'
import { findWorkspaceForPath, WORKSPACES } from './workspaces'

const EXPECTED_FEATURE_PATHS = [
  '/executive', '/executive/pipeline',
  '/opportunity/discovery', '/opportunity/qualification', '/opportunity/monitoring',
  '/tender', '/tender/boq', '/tender/pricing', '/tender/compliance',
  '/tender/competitors', '/tender/submission', '/tender/award',
  '/trust/chat', '/trust/agents',
  '/knowledge/market', '/knowledge/documents', '/knowledge/intelligence',
  '/knowledge/sor', '/knowledge/analytics', '/knowledge/analytics-dashboard',
  '/knowledge/feedback', '/knowledge/clauses', '/knowledge/rule-graph',
  '/knowledge/ppr2025', '/knowledge/document-tools', '/knowledge/learning',
  '/knowledge/search',
  '/enterprise/clients', '/enterprise/team', '/enterprise/settings',
  '/enterprise/audit', '/enterprise/roi', '/enterprise/rbac',
  '/documents', '/team', '/settings', '/admin/dashboard', '/admin/agents',
]

describe('workspace feature navigation', () => {
  it('exposes every implemented top-level feature path', () => {
    const paths = new Set(WORKSPACES.flatMap((workspace) => workspace.sections.map((section) => section.path)))

    for (const path of EXPECTED_FEATURE_PATHS) {
      expect(paths.has(path), `${path} is missing from workspace navigation`).toBe(true)
    }
  })

  it('maps management feature routes to the management workspace', () => {
    for (const path of ['/documents', '/team', '/settings', '/admin/dashboard', '/admin/agents']) {
      expect(findWorkspaceForPath(path).id).toBe('management')
    }
  })
})
