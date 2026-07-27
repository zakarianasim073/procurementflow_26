import { HelpCircle, Search, TrendingUp, ExternalLink } from 'lucide-react'
import { Skeleton } from '@shared/ui/Skeleton'
import { useFaq } from '@hooks/index'

const FALLBACK_FAQS = [
  { id: '1', question: 'What are the key requirements for contractor eligibility?', answer: 'Contractors must demonstrate relevant experience, financial capacity, and technical expertise for the specific work scope.', category: 'Eligibility', relevance: 95 },
  { id: '2', question: 'What documents are required for tender submission?', answer: 'Required documents include technical proposal, financial proposal, company profile, work experience certificates, bank guarantees, and insurance certificates.', category: 'Documentation', relevance: 87 },
  { id: '3', question: 'How is the work quality assessed during execution?', answer: 'Quality is assessed through regular inspections, progress reports, compliance with specifications, and adherence to safety standards.', category: 'Quality', relevance: 82 },
  { id: '4', question: 'What are the dispute resolution mechanisms?', answer: 'Disputes are resolved through mediation, arbitration, or court proceedings as specified in the contract.', category: 'Legal', relevance: 78 },
  { id: '5', question: 'How are variations and change orders handled?', answer: 'Variations require written authorization, impact assessment, and cost approval.', category: 'Variations', relevance: 91 },
]

export function FaqPanel() {
  const { data: faqData, isLoading } = useFaq()
  const faqs = faqData && faqData.length >= 3 ? faqData : FALLBACK_FAQS

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="border-b border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/60">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Frequently Asked Questions</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Common questions and answers for construction procurement
        </p>
      </div>
      
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-none" />)
        ) : faqs.map((faq) => (
          <div key={faq.id} className="group p-4 hover:bg-gray-50 dark:hover:bg-gray-700/60 transition-colors cursor-pointer">
            <div className="flex items-start justify-between">
              <div className="flex-1 pr-4">
                <div className="flex items-center gap-2 mb-2">
                  <HelpCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <span className="text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded">
                    {faq.category}
                  </span>
                  <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                    <TrendingUp className="h-3 w-3" />
                    <span>{faq.relevance}% relevance</span>
                  </div>
                </div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-white leading-relaxed mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                  {faq.question}
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                  {faq.answer}
                </p>
              </div>
              <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                <ExternalLink className="h-4 w-4 text-gray-400" />
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <div className="border-t border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/60">
        <button
          className="w-full flex items-center justify-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          onClick={() => window.open('#', '_blank')}
        >
          <Search className="h-4 w-4" />
          Search more questions
        </button>
      </div>
    </div>
  )
}
