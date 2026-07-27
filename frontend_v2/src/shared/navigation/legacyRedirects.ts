/**
 * Maps every one of frontend/'s 30 existing routes (per docs/frontend/02_INFORMATION_ARCHITECTURE.md's
 * page table) to its new workspace/section path in frontend_v2. Consumed by the router (PFX-05) to
 * render a <Navigate replace> for each old path — no bookmark or deep link should 404.
 *
 * '/login', '/sso/oidc/callback', '/sso/saml/callback' are intentionally absent: they keep their
 * path unchanged (pre-workspace, see docs/frontend/07_NAVIGATION.md).
 */
export const LEGACY_REDIRECTS: Record<string, string> = {
  '/': '/executive',
  '/executive': '/executive',
  '/pipeline': '/executive/pipeline',

  '/search': '/opportunity/discovery',
  '/live-tenders': '/opportunity/discovery',
  '/egp-alerts': '/opportunity/discovery',
  '/tender-qualify': '/opportunity/qualification',
  '/recommend': '/opportunity/qualification',
  '/win-probability': '/opportunity/qualification',
  '/watchdog': '/opportunity/monitoring',
  '/bwdb-monitor': '/opportunity/monitoring',

  '/boq': '/tender/boq',
  '/sor': '/tender/pricing',
  '/price-prediction': '/tender/pricing',
  '/ppr2025': '/tender/compliance',
  '/competitor-benchmark': '/tender/competitors',
  '/award-execution': '/tender/award',

  '/chat': '/trust/chat',
  '/agents': '/trust/agents',

  '/market-trends': '/knowledge/market',
  '/data-intelligence': '/knowledge/market',
  '/resume-generator': '/knowledge/documents',
  '/vat-tax-calculator': '/knowledge/documents',
  '/capacity-risk': '/knowledge/analytics',
  '/analytics': '/knowledge/analytics',

  '/clients': '/enterprise/clients',
  '/team': '/enterprise/team',
  '/settings': '/enterprise/settings',
  '/enterprise': '/enterprise/rbac',
}
