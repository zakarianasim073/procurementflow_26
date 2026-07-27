import { fetchJson } from '../sharedApi'

const BASE = '/api/v2/clean-intel'

export interface CatalogueEntry { dataset: string; rows: number }
export interface DatasetPage {
  dataset: string
  total: number
  rows: Record<string, unknown>[]
}

/** All available clean_intel datasets with row counts. */
export function getCatalogue(): Promise<CatalogueEntry[]> {
  return fetchJson<CatalogueEntry[]>(`${BASE}/catalogue?works_only=true`, true)
}

/** Paginated rows of one dataset; each row is the source JSONB record. */
export function getDataset(
  dataset: string, limit = 50, offset = 0, q?: string,
): Promise<DatasetPage> {
  const p = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (q) p.set('q', q)
  return fetchJson<DatasetPage>(`${BASE}/${dataset}?${p}`, true)
}
