import { FileText, BarChart3, Download, Upload, Search } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Card } from '@shared/ui/Card'
import { Button } from '@shared/ui/Button'
import { Skeleton } from '@shared/ui/Skeleton'
import { ScreenTemplate } from '@layouts/index'
import { useRecentAgentRuns } from '@hooks/index'

const TOOLS = [
  {
    icon: FileText,
    title: 'Resume Generator',
    description: 'Generate contractor resumes from company data',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    slug: 'resume',
  },
  {
    icon: BarChart3,
    title: 'VAT/Tax Calculator',
    description: 'Calculate VAT and tax implications for tender pricing',
    color: 'text-green-500',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    slug: 'vat-tax',
  },
  {
    icon: FileText,
    title: 'BOQ Estimator',
    description: 'Quick BOQ estimation from SOR rates',
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    slug: 'boq-estimator',
  },
  {
    icon: Download,
    title: 'Document Export',
    description: 'Export tenders and analysis to PDF/Excel',
    color: 'text-orange-500',
    bgColor: 'bg-orange-50 dark:bg-orange-900/20',
    slug: 'export',
  },
  {
    icon: Upload,
    title: 'Bulk Upload',
    description: 'Bulk upload tender documents and data',
    color: 'text-cyan-500',
    bgColor: 'bg-cyan-50 dark:bg-cyan-900/20',
    slug: 'bulk-upload',
  },
  {
    icon: Search,
    title: 'SOR Lookup',
    description: 'Quick SOR rate lookup and comparison',
    color: 'text-pink-500',
    bgColor: 'bg-pink-50 dark:bg-pink-900/20',
    slug: 'sor-lookup',
  },
]

export function DocumentToolsPage() {
  const navigate = useNavigate()
  return (
    <ScreenTemplate
      header={
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Document Tools</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Utilities for document processing and generation</p>
        </div>
      }
      primary={
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {TOOLS.map((tool) => (
            <Card key={tool.title} className="p-6 transition-colors hover:border-gray-300 dark:hover:border-gray-600">
              <div className={`inline-flex rounded-lg p-3 ${tool.bgColor}`}>
                <tool.icon className={`h-6 w-6 ${tool.color}`} />
              </div>
              <h3 className="mt-4 text-sm font-semibold text-gray-900 dark:text-white">{tool.title}</h3>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{tool.description}</p>
              <Button
                variant="secondary"
                className="mt-4 w-full"
                onClick={() => navigate(`/knowledge/document-tools/${tool.slug}`)}
              >
                Launch Tool
              </Button>
            </Card>
          ))}
        </div>
      }
    />
  )
}
