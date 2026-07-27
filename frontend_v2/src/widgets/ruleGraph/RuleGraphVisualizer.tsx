import { useState } from 'react'
import { BarChart3, RotateCcw } from 'lucide-react'

interface Node {
  id: string
  label: string
  cluster: 'qualification' | 'evaluation' | 'award' | 'contract'
}

interface Edge {
  source: string
  target: string
  type: 'requires' | 'contradicts' | 'overrides' | 'clarifies'
}

interface RuleGraphVisualizerProps {
  nodes?: Node[]
  edges?: Edge[]
  onNodeClick?: (nodeId: string) => void
  layout?: 'cluster' | 'hierarchy' | 'force'
}

const mockNodes: Node[] = [
  { id: 'r31', label: 'R31', cluster: 'qualification' },
  { id: 'r37', label: 'R37', cluster: 'qualification' },
  { id: 'r38', label: 'R38', cluster: 'qualification' },
  { id: 'r40', label: 'R40', cluster: 'qualification' },
  { id: 'r42', label: 'R42', cluster: 'evaluation' },
  { id: 'r43', label: 'R43', cluster: 'evaluation' },
  { id: 'r45', label: 'R45', cluster: 'award' },
  { id: 'r51', label: 'R51', cluster: 'contract' },
]

const mockEdges: Edge[] = [
  { source: 'r37', target: 'r42', type: 'requires' },
  { source: 'r38', target: 'r42', type: 'requires' },
  { source: 'r40', target: 'r42', type: 'requires' },
  { source: 'r42', target: 'r43', type: 'requires' },
  { source: 'r43', target: 'r45', type: 'requires' },
]

const clusterColors = {
  qualification: 'bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-300',
  evaluation: 'bg-orange-100 text-orange-900 dark:bg-orange-900/40 dark:text-orange-300',
  award: 'bg-purple-100 text-purple-900 dark:bg-purple-900/40 dark:text-purple-300',
  contract: 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-300',
}

const edgeColors = {
  requires: 'stroke-green-500',
  contradicts: 'stroke-red-500',
  overrides: 'stroke-orange-500',
  clarifies: 'stroke-blue-500',
}

export function RuleGraphVisualizer({
  nodes = mockNodes,
  edges = mockEdges,
  onNodeClick,
  layout = 'cluster',
}: RuleGraphVisualizerProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [currentLayout, setCurrentLayout] = useState<'cluster' | 'hierarchy' | 'force'>(layout)
  const [showFilters, setShowFilters] = useState(false)

  const handleNodeClick = (nodeId: string) => {
    setSelectedNode(nodeId)
    onNodeClick?.(nodeId)
  }

  // Simple positioning based on layout
  const getPosition = (nodeId: string, index: number) => {
    const node = nodes.find((n) => n.id === nodeId)
    if (!node) return { x: 0, y: 0 }

    switch (currentLayout) {
      case 'hierarchy': {
        const col = ['qualification', 'evaluation', 'award', 'contract'].indexOf(node.cluster)
        return { x: 100 + col * 150, y: 100 + (index % 3) * 100 }
      }
      case 'force': {
        return { x: 50 + Math.random() * 400, y: 50 + Math.random() * 300 }
      }
      case 'cluster':
      default: {
        const clusters = {
          qualification: { x: 100, y: 100 },
          evaluation: { x: 100, y: 300 },
          award: { x: 350, y: 300 },
          contract: { x: 350, y: 100 },
        }
        const base = clusters[node.cluster]
        return { x: base.x + (index % 2) * 80, y: base.y + (Math.floor(index / 2) % 2) * 80 }
      }
    }
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex gap-2 flex-wrap">
        <div className="flex gap-1">
          {(['cluster', 'hierarchy', 'force'] as const).map((l) => (
            <button
              key={l}
              onClick={() => setCurrentLayout(l)}
              className={`px-3 py-2 text-xs font-medium rounded border transition-colors ${
                currentLayout === l
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900'
              }`}
            >
              {l === 'cluster' ? 'Cluster' : l === 'hierarchy' ? 'Hierarchy' : 'Force'}
            </button>
          ))}
        </div>

        <button
          onClick={() => setShowFilters(!showFilters)}
          className="px-3 py-2 text-xs font-medium rounded border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900"
        >
          <BarChart3 className="h-4 w-4 inline mr-1" />
          Filters
        </button>

        <button className="px-3 py-2 text-xs font-medium rounded border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900">
          <RotateCcw className="h-4 w-4 inline mr-1" />
          Reset
        </button>
      </div>

      {/* Graph Canvas */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden" style={{ height: '400px' }}>
        <svg width="100%" height="100%" className="bg-gray-50 dark:bg-gray-900/30">
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
            </marker>
          </defs>

          {/* Edges */}
          {edges.map((edge, idx) => {
            const sourcePos = getPosition(edge.source, nodes.findIndex((n) => n.id === edge.source))
            const targetPos = getPosition(edge.target, nodes.findIndex((n) => n.id === edge.target))

            return (
              <line
                key={idx}
                x1={sourcePos.x + 30}
                y1={sourcePos.y + 30}
                x2={targetPos.x + 30}
                y2={targetPos.y + 30}
                className={`${edgeColors[edge.type]} opacity-60`}
                strokeWidth="2"
                markerEnd="url(#arrowhead)"
              />
            )
          })}

          {/* Nodes */}
          {nodes.map((node, idx) => {
            const pos = getPosition(node.id, idx)
            const isSelected = node.id === selectedNode
            const isConnected = edges.some((e) => e.source === node.id || e.target === node.id)

            return (
              <g key={node.id} onClick={() => handleNodeClick(node.id)} style={{ cursor: 'pointer' }}>
                <circle
                  cx={pos.x + 30}
                  cy={pos.y + 30}
                  r={isSelected ? 35 : 28}
                  className={`${clusterColors[node.cluster]} transition-all ${isSelected ? 'ring-2 ring-blue-600' : ''}`}
                  opacity={isConnected || !selectedNode ? 1 : 0.3}
                />
                <text
                  x={pos.x + 30}
                  y={pos.y + 32}
                  textAnchor="middle"
                  className="font-bold text-xs fill-current"
                  pointerEvents="none"
                >
                  {node.label}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <p className="mb-3 text-xs font-semibold text-gray-900 dark:text-white">Clusters & Relationships</p>
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div className="space-y-2">
            {Object.entries(clusterColors).map(([cluster, colors]) => (
              <div key={cluster} className="flex items-center gap-2">
                <div className={`w-4 h-4 rounded ${colors}`} />
                <span className="text-gray-700 dark:text-gray-300 capitalize">{cluster}</span>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            {Object.entries(edgeColors).map(([rel, color]) => (
              <div key={rel} className="flex items-center gap-2">
                <svg width="16" height="16" viewBox="0 0 16 16">
                  <line x1="0" y1="8" x2="16" y2="8" className={color} strokeWidth="2" />
                </svg>
                <span className="text-gray-700 dark:text-gray-300 capitalize">{rel}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
