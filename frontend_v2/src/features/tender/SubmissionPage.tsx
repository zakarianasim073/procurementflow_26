import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Clock, FileText, Plus } from 'lucide-react'
import { Card } from '@shared/ui/Card'
import { Badge } from '@shared/ui/Badge'
import { Button } from '@shared/ui/Button'
import { Input } from '@shared/ui/Input'
import { Skeleton } from '@shared/ui/Skeleton'
import { EmptyState } from '@shared/ui/EmptyState'
import { ScreenTemplate } from '@layouts/index'
import { useSubmissions, useUpdateSubmissionStatus } from '@hooks/index'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  preparing: 'info',
  ready: 'success',
  submitted: 'success',
  under_review: 'warning',
  accepted: 'success',
  rejected: 'danger',
}

export function SubmissionPage() {
  const navigate = useNavigate()
  const [tenderId, setTenderId] = useState('')

  const { data: submissions, isLoading } = useSubmissions(tenderId || undefined)
  const _updateStatus = useUpdateSubmissionStatus()

  return (
    <ScreenTemplate
      header={
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/tender')} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <ArrowLeft size={18} />
          </button>
          <div className="flex-1">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Submission Tracker</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Track tender submissions and deadlines</p>
          </div>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Submission
          </Button>
        </div>
      }
      primary={
        <div className="space-y-6">
          <Card className="p-4">
            <Input
              label="Filter by Tender ID"
              value={tenderId}
              onChange={(e) => setTenderId(e.target.value)}
              placeholder="Optional: filter by tender"
              className="w-64"
            />
          </Card>

          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
            </div>
          ) : !submissions?.length ? (
            <EmptyState
              title="No submissions"
              description="Create a new submission to start tracking."
            />
          ) : (
            <div className="space-y-3">
              {submissions.map((sub) => (
                <Card key={sub.submission_id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-gray-500">{sub.tender_id}</span>
                        <h3 className="text-sm font-medium text-gray-900 dark:text-white">{sub.tender_title}</h3>
                      </div>
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{sub.agency}</p>
                    </div>
                    <Badge variant={STATUS_COLORS[sub.status] as any}>
                      {sub.status.replace(/_/g, ' ')}
                    </Badge>
                  </div>

                  <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Deadline: {sub.deadline ? new Date(sub.deadline).toLocaleDateString() : 'Not available'}
                    </div>
                    <div className="flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      {sub.documents.length} documents
                    </div>
                  </div>

                  {sub.documents.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {sub.documents.map((doc) => (
                        <span key={doc.document_id} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                          {doc.name}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      }
    />
  )
}
