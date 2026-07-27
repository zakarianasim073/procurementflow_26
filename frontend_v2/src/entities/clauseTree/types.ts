export interface ClauseTreeNode {
  id: string
  label: string
  level: 'schedule' | 'section' | 'rule' | 'subsection'
  parent_id?: string
  children: ClauseTreeNode[]
  metadata: {
    ppr_version: 'PPR2025' | 'PPR2008'
    clause_id?: string
    tags: string[]
    mistake_count?: number
    precedent_count?: number
    is_new_in_ppr2025?: boolean
  }
}

export interface ClauseTag {
  id: string
  label: string
  count: number
}
