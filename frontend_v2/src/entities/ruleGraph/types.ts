export type RelationshipType = 'requires' | 'contradicts' | 'overrides' | 'clarifies' | 'example-of' | 'applies-to'

export interface RuleNode {
  id: string
  rule_id: string
  label: string
  cluster: string
  relationship_count: number
}

export interface RuleEdge {
  id: string
  source: string
  target: string
  relationship: RelationshipType
  confidence: 'authoritative' | 'high' | 'medium' | 'interpretive'
  reason: string
  note?: string
}

export interface RuleGraph {
  nodes: RuleNode[]
  edges: RuleEdge[]
}

export interface RuleRelationship {
  id: string
  source_rule: string
  target_rule: string
  relationship: RelationshipType
  metadata: {
    confidence: string
    reason: string
    note?: string
    court_precedent_id?: string
  }
}

export interface RuleCluster {
  id: string
  name: string
  rules: string[]
  theme: 'qualification' | 'technical-eval' | 'financial-eval' | 'award' | 'contract' | 'other'
  description: string
}
