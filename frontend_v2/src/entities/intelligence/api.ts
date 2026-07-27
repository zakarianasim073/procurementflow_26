import { fetchJson } from '@entities/sharedApi'

const V2 = '/api/v2'

export interface PprRule {
  rule_id: string
  category: string
  title: string
  description: string
  is_legal_mandate: boolean
}

export interface RuleCategory {
  id: string
  label: string
  count: number
}

export interface FaqItem {
  id: string
  question: string
  answer: string
  category: string
  relevance: number
}

export interface CourseItem {
  id: string
  title: string
  description: string
  duration: string
  modules: number
  completed_modules: number
  status: 'not_started' | 'in_progress' | 'completed'
}

export interface MarketRateItem {
  item_name: string
  category: string
  unit: string
  current_rate: number
  change_percent: number
  zone: string
}

export interface PricingScenarios {
  scenarios: Record<string, { label: string; discount_pct: number; confidence: number; median_amount_bdt: number }>
}

export interface WinRateItem {
  contractor_name: string
  win_count: number
  total_value_bdt: number
  win_rate_pct: number
  agency_count: number
}

export interface CategoryItem {
  id: string
  label: string
  count: number
}

export interface KnowledgeSearchResult {
  id: string
  title: string
  excerpt: string
  type: string
  source: string
  relevance: number
}

export interface UserSettings {
  full_name: string
  organization: string
  default_zone: string
  notifications_enabled: boolean
}

export async function getCategories(): Promise<CategoryItem[]> {
  return fetchJson<CategoryItem[]>(`${V2}/intelligence/categories`, true)
}

export async function getPprRules(category?: string): Promise<PprRule[]> {
  const params = category ? `?category=${encodeURIComponent(category)}` : ''
  return fetchJson<PprRule[]>(`${V2}/intelligence/rules${params}`, true)
}

export async function getRuleCategories(): Promise<RuleCategory[]> {
  return fetchJson<RuleCategory[]>(`${V2}/intelligence/rules/categories`, true)
}

export async function getFaq(): Promise<FaqItem[]> {
  return fetchJson<FaqItem[]>(`${V2}/intelligence/faq`, true)
}

export async function getCourses(): Promise<CourseItem[]> {
  return fetchJson<CourseItem[]>(`${V2}/intelligence/courses`, true)
}

export async function getMarketTrends(category?: string, zone?: string, limit?: number): Promise<MarketRateItem[]> {
  const p = new URLSearchParams()
  if (category) p.set('category', category)
  if (zone) p.set('zone', zone)
  if (limit) p.set('limit', String(limit))
  const qs = p.toString()
  return fetchJson<MarketRateItem[]>(`${V2}/intelligence/market-trends${qs ? '?' + qs : ''}`, true)
}

export async function getPricingScenarios(): Promise<PricingScenarios> {
  return fetchJson<PricingScenarios>(`${V2}/intelligence/pricing-scenarios`, true)
}

export async function getWinRate(agency?: string, limit?: number): Promise<WinRateItem[]> {
  const p = new URLSearchParams()
  if (agency) p.set('agency', agency)
  if (limit) p.set('limit', String(limit))
  const qs = p.toString()
  return fetchJson<WinRateItem[]>(`${V2}/intelligence/win-rate${qs ? '?' + qs : ''}`, true)
}

export async function searchKnowledge(q: string, limit?: number): Promise<KnowledgeSearchResult[]> {
  const p = new URLSearchParams({ q })
  if (limit) p.set('limit', String(limit))
  return fetchJson<KnowledgeSearchResult[]>(`${V2}/intelligence/knowledge/search?${p.toString()}`, true)
}

export async function getUserSettings(): Promise<UserSettings> {
  return fetchJson<UserSettings>(`${V2}/intelligence/user/settings`, true)
}

export async function saveUserSettings(settings: UserSettings): Promise<UserSettings> {
  return fetchJson<UserSettings>(`${V2}/intelligence/user/settings`, {
    method: 'PUT',
    body: JSON.stringify(settings),
    authed: true,
  })
}
