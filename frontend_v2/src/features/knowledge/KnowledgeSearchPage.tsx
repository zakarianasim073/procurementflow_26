import { useState, useMemo } from 'react'
import { Search, FileText, BarChart3, Building2, Clock } from 'lucide-react'
import { cn } from '@shared/lib/cn'
import { Card } from '@shared/ui/Card'
import { Badge } from '@shared/ui/Badge'
import { Input } from '@shared/ui/Input'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@shared/ui/Tabs'
import { EmptyState } from '@shared/ui/EmptyState'
import { ScreenTemplate } from '@layouts/index'
import { useRecentAgentRuns, useKnowledgeSearch } from '@hooks/index'

interface SearchResult {
  id: string
  title: string
  excerpt: string
  type: 'tender' | 'sor' | 'contractor' | 'knowledge'
  source: string
  relevance: number
}

const FALLBACK_RESULTS: SearchResult[] = [
  { id: '1', title: 'BOQ Analysis Guide', excerpt: 'Step-by-step guide for analyzing Bill of Quantities across agencies...', type: 'knowledge', source: 'Knowledge Base', relevance: 0.95 },
  { id: '2', title: 'BWDB Zone A SOR Rates', excerpt: 'Complete Schedule of Rates for BWDB Zone A covering construction items...', type: 'sor', source: 'SOR Database', relevance: 0.88 },
  { id: '3', title: 'PPR 2025 Compliance Rules', excerpt: 'Public Procurement Rules 2025 compliance requirements and checklists...', type: 'knowledge', source: 'Policy Documents', relevance: 0.85 },
  { id: '4', title: 'ABC Construction Ltd', excerpt: 'Contractor profile with 45 completed projects, 78% win rate...', type: 'contractor', source: 'Contractor DB', relevance: 0.82 },
]

const TYPE_ICONS: Record<string, typeof FileText> = {
  tender: FileText,
  sor: BarChart3,
  contractor: Building2,
  knowledge: FileText,
}

const TYPE_COLORS: Record<string, string> = {
  tender: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  sor: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  contractor: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  knowledge: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
}

export function KnowledgeSearchPage() {
  const [query, setQuery] = useState('')
  const [activeTab, setActiveTab] = useState('all')
  const { data: runsRes } = useRecentAgentRuns(20)
  const { data: searchRes } = useKnowledgeSearch(query)

  const results: SearchResult[] = useMemo(() => {
    if (query.length >= 2 && searchRes && searchRes.length > 0) {
      return searchRes.map((r: any, i: number) => ({
        id: r.id ?? `sr-${i}`,
        title: r.title,
        excerpt: r.excerpt,
        type: (r.type === 'knowledge' ? 'knowledge' : r.type === 'sor' ? 'sor' : r.type === 'contractor' ? 'contractor' : 'tender') as SearchResult['type'],
        source: r.source ?? 'Knowledge Base',
        relevance: r.relevance ?? 0.8,
      }))
    }
    const fromRuns: SearchResult[] = (runsRes ?? []).slice(0, 10).map((r, i) => ({
      id: `run-${r.run_id ?? i}`,
      title: `${r.agent_name ?? r.agent_id} — ${r.status}`,
      excerpt: `Agent run ${r.execution_time_ms ? `completed in ${(r.execution_time_ms / 1000).toFixed(1)}s` : 'completed'} on ${new Date(r.timestamp ?? Date.now()).toLocaleDateString()}`,
      type: 'sor' as const,
      source: 'Agent Registry',
      relevance: r.status === 'success' ? 0.9 : 0.3,
    }))
    return fromRuns.length > 0 ? fromRuns : FALLBACK_RESULTS
  }, [runsRes, searchRes, query])

  const filteredResults = query
    ? results.filter(r => r.title.toLowerCase().includes(query.toLowerCase()) || r.excerpt.toLowerCase().includes(query.toLowerCase()))
    : results

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Knowledge Search</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Search across tenders, SOR rates, contractors, and knowledge base</p>
        </div>
      }
      primary={
        <div className="space-y-6">
          {/* Search Bar */}
          <Card className="p-4">
            <Input
              label="Search Knowledge Base"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by keyword, code, or topic..."
              leftAddon={<Search className="h-4 w-4 text-gray-400" />}
            />
          </Card>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="all">All Results</TabsTrigger>
              <TabsTrigger value="tender">Tenders</TabsTrigger>
              <TabsTrigger value="sor">SOR Rates</TabsTrigger>
              <TabsTrigger value="contractor">Contractors</TabsTrigger>
              <TabsTrigger value="knowledge">Knowledge</TabsTrigger>
            </TabsList>

            <TabsContent value="all">
              {filteredResults.length === 0 ? (
                <EmptyState
                  title="No results found"
                  description="Try a different search term."
                />
              ) : (
                <div className="space-y-3">
                  {filteredResults.map((result) => {
                    const Icon = TYPE_ICONS[result.type] || FileText
                    return (
                      <Card key={result.id} className="p-4 transition-colors hover:border-gray-300 dark:hover:border-gray-600">
                        <div className="flex items-start gap-3">
                          <div className={cn('rounded-lg p-2', TYPE_COLORS[result.type])}>
                            <Icon className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{result.title}</h3>
                              <Badge tone="default">{result.type}</Badge>
                            </div>
                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{result.excerpt}</p>
                            <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
                              <span className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {result.source}
                              </span>
                              <span>Relevance: {Math.round(result.relevance * 100)}%</span>
                            </div>
                          </div>
                        </div>
                      </Card>
                    )
                  })}
                </div>
              )}
            </TabsContent>

            {['tender', 'sor', 'contractor', 'knowledge'].map(tab => (
              <TabsContent key={tab} value={tab}>
                <div className="space-y-3">
                  {filteredResults.filter(r => r.type === tab).map((result) => {
                    const Icon = TYPE_ICONS[result.type] || FileText
                    return (
                      <Card key={result.id} className="p-4">
                        <div className="flex items-start gap-3">
                          <div className={cn('rounded-lg p-2', TYPE_COLORS[result.type])}>
                            <Icon className="h-5 w-5" />
                          </div>
                          <div>
                            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{result.title}</h3>
                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{result.excerpt}</p>
                          </div>
                        </div>
                      </Card>
                    )
                  })}
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </div>
      }
    />
  )
}
