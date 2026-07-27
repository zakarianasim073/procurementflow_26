import { useState, useMemo } from 'react'
import { ScreenTemplate } from '@layouts/index'
import { RuleGraphVisualizer, RuleGraphDetailPanel, RuleGraphControlPanel } from '@widgets/ruleGraph'
import { useRuleGraph } from '@hooks/ruleGraph'
import type { RuleEdge } from '@entities/ruleGraph/types'

function edgeToRelationships(edges: RuleEdge[], nodeId: string, direction: 'incoming' | 'outgoing') {
  const filtered = edges.filter((e) => direction === 'incoming' ? e.target === nodeId : e.source === nodeId)
  return filtered
    .filter((e): e is RuleEdge & { relationship: 'requires' | 'contradicts' | 'overrides' | 'clarifies' } =>
      ['requires', 'contradicts', 'overrides', 'clarifies'].includes(e.relationship))
    .map((e) => ({
      type: e.relationship,
      targetRuleId: direction === 'incoming' ? e.source : e.target,
      targetRuleLabel: '',
    }))
}

export function RuleGraphPage() {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [layout, setLayout] = useState<'cluster' | 'hierarchy' | 'force'>('cluster')
  const [relationshipFilter, setRelationshipFilter] = useState<string[]>(['requires', 'contradicts', 'overrides', 'clarifies'])

  const { data: graph, isLoading } = useRuleGraph()
  const nodes = graph?.nodes ?? []
  const edges = graph?.edges ?? []
  const visualNodes = nodes.map((node) => ({
    id: node.id,
    label: node.label,
    cluster: (['qualification', 'evaluation', 'award', 'contract'].includes(node.cluster)
      ? node.cluster
      : 'qualification') as 'qualification' | 'evaluation' | 'award' | 'contract',
  }))
  const visualEdges = edges
    .filter((edge) => ['requires', 'contradicts', 'overrides', 'clarifies'].includes(edge.relationship))
    .map((edge) => ({
      source: edge.source,
      target: edge.target,
      type: edge.relationship as 'requires' | 'contradicts' | 'overrides' | 'clarifies',
    }))

  const selectedNode = useMemo(() => nodes.find((n) => n.id === selectedNodeId), [nodes, selectedNodeId])

  const incomingRelationships = useMemo(
    () => edgeToRelationships(edges, selectedNodeId ?? '', 'incoming'),
    [edges, selectedNodeId],
  )
  const outgoingRelationships = useMemo(
    () => edgeToRelationships(edges, selectedNodeId ?? '', 'outgoing'),
    [edges, selectedNodeId],
  )

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Rule Graph Visualizer</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">Visualize PPR2025 rule dependencies: requirements, contradictions, clarifications</p>
        </div>
      }
      primary={
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          <div className="lg:col-span-1">
            <RuleGraphControlPanel
              layout={layout}
              onLayoutChange={setLayout}
              relationshipTypes={relationshipFilter as any}
              onFilterChange={setRelationshipFilter}
            />
          </div>

          <div className="lg:col-span-2">
            {isLoading ? (
              <div className="flex items-center justify-center h-64 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                <p className="text-sm text-gray-500">Loading rule graph...</p>
              </div>
            ) : (
              <RuleGraphVisualizer
                nodes={visualNodes}
                edges={visualEdges}
                layout={layout}
                onNodeClick={setSelectedNodeId}
              />
            )}
          </div>

          <div className="lg:col-span-1">
            {selectedNode ? (
              <RuleGraphDetailPanel
                ruleId={selectedNode.label || selectedNode.id}
                ruleLabel={selectedNode.cluster}
                description={`Rule ${selectedNode.label || selectedNode.id}`}
                incomingRelationships={incomingRelationships}
                outgoingRelationships={outgoingRelationships}
                onClose={() => setSelectedNodeId(null)}
              />
            ) : (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 text-center">
                <p className="text-sm text-gray-600 dark:text-gray-400">Click a node to view details</p>
              </div>
            )}
          </div>
        </div>
      }
    >
    </ScreenTemplate>
  )
}
