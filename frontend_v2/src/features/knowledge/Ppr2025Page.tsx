import { useState } from 'react'
import { FileText, CheckCircle, AlertCircle, BookOpen, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { ScreenTemplate } from '@layouts/index'
import { Skeleton } from '@shared/ui/Skeleton'
import { usePprRules } from '@hooks/index'
import { fetchJson } from '@entities/sharedApi'

type TabType = 'rules' | 'checker' | 'reports' | 'guidelines'

export function Ppr2025Page() {
  const [activeTab, setActiveTab] = useState<TabType>('rules')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const { data: rulesData, isLoading } = usePprRules(selectedCategory === 'all' ? undefined : selectedCategory)
  const [guidelineQuery, setGuidelineQuery] = useState('')
  const guidelines = useQuery({
    queryKey: ['ppr2025-guidelines', guidelineQuery],
    queryFn: () => fetchJson<{
      total: number
      source: { title: string; source_file: string; character_count: number; section_count: number; updated_at: string } | null
      sections: Array<{ id: string; section_ref: string; title: string; content: string }>
    }>(`/api/ppr2025/guidelines?q=${encodeURIComponent(guidelineQuery)}&limit=100`),
    enabled: activeTab === 'guidelines',
  })

  const categories = [
    { id: 'all', label: 'All Rules', icon: '📋' },
    { id: 'financial_security', label: 'Financial Security', icon: '🔒' },
    { id: 'procurement_method', label: 'Procurement Method', icon: '🏆' },
    { id: 'eligibility', label: 'Eligibility', icon: '✅' },
    { id: 'slt_alt', label: 'SLT/ALT', icon: '📊' },
  ]

  const tabs = [
    { id: 'rules', label: 'Rules', icon: FileText },
    { id: 'checker', label: 'Compliance Checker', icon: CheckCircle },
    { id: 'reports', label: 'Reports', icon: AlertCircle },
    { id: 'guidelines', label: 'Guidelines', icon: BookOpen },
  ]

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-green-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">PPR 2025 Compliance</h1>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">Public Procurement Rules 2025 compliance guidance and checker</p>
          </div>
        </div>
      }
      primary={
        <div className="space-y-6">
          {/* Tab Navigation */}
          <div className="border-b border-gray-200 dark:border-gray-700">
            <div className="flex gap-4">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as TabType)}
                    className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                        : 'border-transparent text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300'
                    }`}
                  >
                    <Icon size={18} />
                    {tab.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Rules Tab */}
          {activeTab === 'rules' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      selectedCategory === cat.id
                        ? 'border-blue-600 bg-blue-50 text-blue-600 dark:border-blue-400 dark:bg-blue-950/30 dark:text-blue-400'
                        : 'border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800'
                    }`}
                  >
                    <span className="mr-2">{cat.icon}</span>
                    {cat.label}
                  </button>
                ))}
              </div>

              {isLoading ? (
                <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}</div>
              ) : rulesData && rulesData.length > 0 ? (
                <div className="space-y-3">
                  {rulesData.map((rule) => (
                    <div key={rule.rule_id} className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-semibold text-gray-900 dark:text-white">{rule.title}</h3>
                          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{rule.description}</p>
                        </div>
                        <span className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${
                          rule.is_legal_mandate
                            ? 'bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400'
                        }`}>
                          {rule.is_legal_mandate ? 'Core' : 'Guideline'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-gray-200 p-6 text-center dark:border-gray-700">
                  <p className="text-sm text-gray-500">No rules found for this category.</p>
                </div>
              )}
            </div>
          )}

          {/* Compliance Checker Tab */}
          {activeTab === 'checker' && (
            <div className="rounded-lg border border-gray-200 p-6 dark:border-gray-700">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Check Tender Compliance</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-white">Tender Type</label>
                  <select className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white">
                    <option>Competitive Bidding</option>
                    <option>Single Source</option>
                    <option>Emergency</option>
                    <option>RE-bidding</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-white">Procurement Value (BDT)</label>
                  <input
                    type="number"
                    placeholder="Enter amount"
                    className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-white">Procuring Entity</label>
                  <input
                    type="text"
                    placeholder="e.g., BWDB, LGED, PWD"
                    className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </div>

                <button className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600">
                  Check Compliance
                </button>
              </div>

              <div className="mt-6 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950/30">
                <p className="text-sm text-green-800 dark:text-green-200">✓ No compliance issues found</p>
              </div>
            </div>
          )}

          {/* Reports Tab */}
          {activeTab === 'reports' && (
            <div className="rounded-lg border border-gray-200 p-6 dark:border-gray-700">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Compliance Reports</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">No compliance reports available yet. Run a compliance check to generate one.</p>
            </div>
          )}

          {/* Guidelines Tab */}
          {activeTab === 'guidelines' && (
            <div className="space-y-4">
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950/30">
                <h3 className="font-semibold text-blue-900 dark:text-blue-200">{guidelines.data?.source?.title || 'PPR 2025 Guidelines'}</h3>
                <p className="mt-1 text-sm text-blue-800 dark:text-blue-300">
                  {guidelines.data?.source ? `${guidelines.data.source.section_count} searchable database sections · ${guidelines.data.source.character_count.toLocaleString()} characters` : 'Loading the supplied guideline from PostgreSQL…'}
                </p>
                {guidelines.data?.source && <p className="mt-1 break-all text-xs text-blue-700 dark:text-blue-400">Source: {guidelines.data.source.source_file}</p>}
              </div>

              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <input value={guidelineQuery} onChange={event => setGuidelineQuery(event.target.value)} placeholder="Search tender security, evaluation, SLT, forms…" className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-10 pr-4 text-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white" />
              </div>

              {guidelines.isLoading ? <div className="space-y-3">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28 w-full rounded-xl" />)}</div> : guidelines.error ? (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{guidelines.error.message}</div>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs text-gray-500">{guidelines.data?.total ?? 0} matching sections</p>
                  {(guidelines.data?.sections ?? []).map(section => (
                    <details key={section.id} className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
                      <summary className="cursor-pointer list-none font-medium text-gray-900 dark:text-white"><span className="mr-2 font-mono text-xs text-blue-600">{section.section_ref}</span>{section.title}</summary>
                      <div className="mt-3 whitespace-pre-wrap border-t border-gray-100 pt-3 text-sm leading-6 text-gray-700 dark:border-gray-800 dark:text-gray-300">{section.content}</div>
                    </details>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      }
    />
  )
}
