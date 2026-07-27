export interface SorRate {
  code: string
  description?: string
  unit?: string
  agency: string
  zone_a?: number
  zone_b?: number
  zone_c?: number
  zone_d?: number
  rate?: number
  zone: string
}

export interface SorSearchResult {
  rates: SorRate[]
  total_count: number
  query: string
}

export interface SorAgency {
  id: string
  name: string
  total_rates: number
  has_csv: boolean
}

export interface SorComparison {
  code: string
  description?: string
  unit?: string
  rates: Record<string, number>
  variance: number
}
