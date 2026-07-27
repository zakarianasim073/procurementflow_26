export interface ClauseMistake {
  id: string
  description: string
  consequence: string
  frequency: 'rare' | 'occasional' | 'common' | 'very common'
  from_tender_ids?: string[]
}

export interface ClauseTecDecision {
  id: string
  tender_id: string
  ruling: string
  date: string
  source: string
}

export interface ClausePrecedent {
  id: string
  case_name: string
  court: string
  year: number
  holding: string
  relevance: string
  link?: string
}

export interface ClauseRelated {
  rule_id: string
  relationship: 'requires' | 'contradicts' | 'overrides' | 'clarifies' | 'example-of'
  note: string
}

export interface ClauseFaq {
  question: string
  answer: string
  from_feedback?: boolean
}

export interface ClauseExample {
  scenario: string
  good_practice: string
  bad_practice: string
}

export interface Clause {
  id: string
  ppr_version: 'PPR2008' | 'PPR2025'
  rule_number: string
  schedule?: string
  title: string
  content: {
    official_text: string
    plain_english_summary: string
    intent: string
  }
  common_mistakes: ClauseMistake[]
  tec_decisions: ClauseTecDecision[]
  court_precedents: ClausePrecedent[]
  related_clauses: ClauseRelated[]
  faq: ClauseFaq[]
  examples: ClauseExample[]
  last_updated: string
  updated_by: string
  confidence_level: 'official' | 'high' | 'medium' | 'interpretive'
  tags: string[]
}

export interface ClauseListItem {
  id: string
  rule_number: string
  title: string
  schedule?: string
  confidence_level: Clause['confidence_level']
  tags: string[]
  mistake_count: number
  precedent_count: number
}

export interface ClauseListResult {
  clauses: ClauseListItem[]
  total: number
  page: number
  page_size: number
}
