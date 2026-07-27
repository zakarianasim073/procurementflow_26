import { useState } from 'react'
import { ChevronDown, Search } from 'lucide-react'
import { useClauseTree } from '@hooks/clauseTree'

interface ClauseNode {
  id: string
  label: string
  level: 'schedule' | 'section' | 'rule' | 'subsection'
  children?: ClauseNode[]
  mistakeCount?: number
  precedentCount?: number
}

interface ClauseTreeProps {
  root?: ClauseNode
  activeClauseId?: string
  onSelectClause?: (clauseId: string) => void
  filter?: { tags?: string[]; search?: string }
}

const mockRoot: ClauseNode = {
  id: 'ppr2025',
  label: 'PPR2025',
  level: 'schedule',
  children: [
    {
      id: 'sch2',
      label: 'Schedule 2: Instructions to Tenderers',
      level: 'schedule',
      children: [
        {
          id: 'sch2-a',
          label: 'Section A: Tender Submission',
          level: 'section',
          children: [
            { id: 'r21', label: 'R21 — Tender Format', level: 'rule', mistakeCount: 2 },
            { id: 'r22', label: 'R22 — Submission Deadlines', level: 'rule', mistakeCount: 5 },
          ],
        },
        {
          id: 'sch2-b',
          label: 'Section B: Qualification',
          level: 'section',
          children: [
            { id: 'r31', label: 'R31 — Eligibility', level: 'rule', mistakeCount: 1 },
            { id: 'r37', label: 'R37 — Experience Qualification', level: 'rule', mistakeCount: 8, precedentCount: 3 },
            { id: 'r38', label: 'R38 — Financial Capacity', level: 'rule', mistakeCount: 4 },
            { id: 'r40', label: 'R40 — Technical Capacity', level: 'rule', mistakeCount: 2 },
          ],
        },
        {
          id: 'sch2-c',
          label: 'Section C: Evaluation',
          level: 'section',
          children: [
            { id: 'r42', label: 'R42 — General Evaluation Principles', level: 'rule', mistakeCount: 3, precedentCount: 5 },
            { id: 'r43', label: 'R43 — Financial Evaluation', level: 'rule', mistakeCount: 6 },
            { id: 'r45', label: 'R45 — Award Criteria', level: 'rule', mistakeCount: 2 },
          ],
        },
      ],
    },
    {
      id: 'sch4',
      label: 'Schedule 4: General Conditions of Contract',
      level: 'schedule',
      children: [
        {
          id: 'sch4-a',
          label: 'Part A: General Provisions',
          level: 'section',
          children: [
            { id: 'r61', label: 'R61 — Definitions', level: 'rule', mistakeCount: 0 },
            { id: 'r65', label: 'R65 — Obligations', level: 'rule', mistakeCount: 3 },
          ],
        },
      ],
    },
  ],
}

function getMistakeColor(count?: number) {
  if (!count) return 'text-gray-600 dark:text-gray-400'
  if (count <= 3) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/30'
  if (count <= 6) return 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30'
  return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30'
}

function TreeNode({
  node,
  activeClauseId,
  onSelectClause,
  expanded,
  onToggle,
}: {
  node: ClauseNode
  activeClauseId?: string
  onSelectClause?: (id: string) => void
  expanded: Set<string>
  onToggle: (id: string) => void
}) {
  const isExpanded = expanded.has(node.id)
  const hasChildren = node.children && node.children.length > 0
  const isActive = node.id === activeClauseId

  return (
    <div className="select-none">
      <div
        className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
          isActive
            ? 'bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-300'
            : 'hover:bg-gray-100 dark:hover:bg-gray-900/40 text-gray-700 dark:text-gray-300'
        }`}
        onClick={() => onSelectClause?.(node.id)}
      >
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggle(node.id)
            }}
            className="p-0 hover:bg-gray-200 dark:hover:bg-gray-800 rounded"
          >
            <ChevronDown
              className={`h-4 w-4 transition-transform ${isExpanded ? '' : '-rotate-90'}`}
            />
          </button>
        )}
        {!hasChildren && <div className="w-4" />}

        <span className="flex-1 text-sm font-medium">{node.label}</span>

        {node.mistakeCount !== undefined && node.mistakeCount > 0 && (
          <span className={`px-2 py-1 rounded text-xs font-semibold ${getMistakeColor(node.mistakeCount)}`}>
            {node.mistakeCount} ⚠️
          </span>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div className="ml-4 border-l border-gray-200 dark:border-gray-700">
          {node.children?.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              activeClauseId={activeClauseId}
              onSelectClause={onSelectClause}
              expanded={expanded}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function ClauseTree({
  root: _root,
  activeClauseId,
  onSelectClause,
  filter: _filter,
}: ClauseTreeProps) {
  const { data: apiRoot, isLoading } = useClauseTree()
  const root = apiRoot ?? mockRoot
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['ppr2025', 'sch2', 'sch2-b']))
  const [searchTerm, setSearchTerm] = useState('')

  const toggleExpand = (id: string) => {
    const newExpanded = new Set(expanded)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpanded(newExpanded)
  }

  const expandAll = () => {
    const newExpanded = new Set<string>()
    function collectIds(node: ClauseNode) {
      newExpanded.add(node.id)
      node.children?.forEach(collectIds)
    }
    collectIds(root)
    setExpanded(newExpanded)
  }

  const collapseAll = () => {
    setExpanded(new Set([root.id]))
  }

  return (
    <div className="space-y-4">
      {/* Search & Controls */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search rules by # or keyword..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="text-xs px-3 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900 text-gray-700 dark:text-gray-300"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="text-xs px-3 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900 text-gray-700 dark:text-gray-300"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Tree */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 max-h-96 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-32"><p className="text-sm text-gray-500">Loading clause tree...</p></div>
        ) : (
        <TreeNode
          node={root}
          activeClauseId={activeClauseId}
          onSelectClause={onSelectClause}
          expanded={expanded}
          onToggle={toggleExpand}
        />
        )}
      </div>
    </div>
  )
}
