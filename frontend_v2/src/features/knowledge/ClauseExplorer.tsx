import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import { ClauseTree } from '@widgets/clauseTree'
import { ClauseHeader, ClauseText, CommonMistakesPanel, PrecedentCard, RelatedClausesPanel, FaqPanel } from '@widgets/clause'
import { useClause, useRelatedClauses, useClauseTree } from '@hooks/index'

export function ClauseExplorer() {
  const [selectedClauseId, setSelectedClauseId] = useState<string>('R37')
  const [showSidebar, setShowSidebar] = useState(true)

  const { data: clause, isLoading } = useClause(selectedClauseId)
  const { data: related } = useRelatedClauses(selectedClauseId)
  const { data: treeData } = useClauseTree()

  const treeRoot = treeData

  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Clause Knowledge Base</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">Deep dive: official text, interpretations, precedents, FAQs</p>
        </div>
      }
      primary={
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          {showSidebar && (
            <div className="lg:col-span-1">
              <ClauseTree root={treeRoot} activeClauseId={selectedClauseId} onSelectClause={setSelectedClauseId} />
            </div>
          )}

          <div className={showSidebar ? 'lg:col-span-2' : 'lg:col-span-3'}>
            {isLoading ? (
              <div className="flex items-center justify-center py-20"><Loader2 size={24} className="animate-spin text-gray-400" /></div>
            ) : !clause ? (
              <div className="flex items-center justify-center py-20 text-sm text-gray-400">Select a clause from the tree or search for one</div>
            ) : (
              <div className="space-y-6">
                <ClauseHeader
                  clause={{ id: clause.id, code: clause.rule_number, category: clause.schedule ?? 'General', priority: clause.confidence_level === 'official' ? 'high' : 'medium' }}
                />
                <ClauseText
                  clause={{
                    id: clause.id,
                    code: clause.rule_number,
                    title: clause.title,
                    text: clause.content?.official_text ?? '',
                    category: clause.schedule ?? 'General',
                    examples: clause.content?.plain_english_summary ? [clause.content.plain_english_summary] : [],
                    attachments: [],
                  }}
                />
                {clause.common_mistakes?.length > 0 && (
                  <CommonMistakesPanel
                    mistakes={clause.common_mistakes.map((m, i) => ({
                      id: m.id ?? `m${i}`,
                      type: 'technical' as const,
                      severity: (m.frequency === 'common' || m.frequency === 'very common' ? 'moderate' : 'minor') as 'critical' | 'moderate' | 'minor',
                      description: m.description,
                      impact: m.consequence,
                      solution: 'Review requirements carefully',
                      clause_refs: [clause.id],
                    }))}
                  />
                )}
                {clause.court_precedents?.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Court Precedents</h3>
                    {clause.court_precedents.map((precedent) => (
                      <PrecedentCard
                        key={precedent.id ?? precedent.case_name}
                        precedent={{
                          id: precedent.id ?? precedent.case_name,
                          case_reference: precedent.case_name,
                          court: precedent.court,
                          date: String(precedent.year),
                          excerpt: precedent.holding,
                          outcome: precedent.holding,
                          relevance_score: 90,
                          clause_refs: [clause.id],
                        }}
                      />
                    ))}
                  </div>
                )}
                {clause.faq?.length > 0 && <FaqPanel />}
              </div>
            )}
          </div>

          <div className="lg:col-span-1 space-y-6">
            {(related ?? []).length > 0 && (
              <RelatedClausesPanel
                relatedClauses={(related ?? []).map((rc: any) => ({
                  id: rc.rule_id ?? rc.id,
                  code: (rc.rule_id ?? rc.id).toUpperCase(),
                  title: rc.note ?? rc.title ?? '',
                  relevance_score: 90,
                  category: 'Related',
                  summary: rc.note ?? '',
                  last_updated: '2025-01-01',
                }))}
              />
            )}
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="w-full py-2 px-4 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900/50"
            >
              {showSidebar ? 'Hide Tree' : 'Show Tree'}
            </button>
          </div>
        </div>
      }
    />
  )
}
