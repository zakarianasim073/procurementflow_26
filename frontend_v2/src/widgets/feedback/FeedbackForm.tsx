import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSubmitFeedback } from '@hooks/feedback'
import type { FeedbackSubmitPayload } from '@entities/feedback/types'
import { Loader2, Send, AlertCircle } from 'lucide-react'

interface FeedbackFormProps {
  tenderId?: string
  onSuccess?: () => void
}

export function FeedbackForm({ tenderId, onSuccess }: FeedbackFormProps) {
  const navigate = useNavigate()
  const submitFeedbackMutation = useSubmitFeedback()
  const [formData, setFormData] = useState<FeedbackSubmitPayload>({
    tender_id: tenderId || '',
    bid_decision: 'unknown',
    bid_price: 0,
    award_status: 'unknown',
    helpfulness_score: 3,
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    setErrors({})

    if (!formData.tender_id) {
      setErrors({ tender_id: 'Tender ID is required' })
      return
    }
    if (!formData.bid_price || formData.bid_price <= 0) {
      setErrors({ bid_price: 'Bid price is required' })
      return
    }

    try {
      await submitFeedbackMutation.mutateAsync(formData)
      onSuccess?.()
      navigate('/knowledge/feedback')
    } catch (error) {
      console.error('Failed to submit feedback:', error)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      {submitFeedbackMutation.isPending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm font-medium">Submitting feedback...</span>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <label htmlFor="bid_decision" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Bid Decision *
          </label>
          <select
            id="bid_decision"
            value={formData.bid_decision}
            onChange={(e) => setFormData({ ...formData, bid_decision: e.target.value as FeedbackSubmitPayload['bid_decision'] })}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
          >
            <option value="bid">Bid</option>
            <option value="rejected">Rejected</option>
            <option value="unknown">Unknown</option>
          </select>
          {errors.bid_decision && (
            <p className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />
              {errors.bid_decision}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <label htmlFor="award_status" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Award Status *
          </label>
          <select
            id="award_status"
            value={formData.award_status}
            onChange={(e) => setFormData({ ...formData, award_status: e.target.value as FeedbackSubmitPayload['award_status'] })}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
          >
            <option value="won">Won</option>
            <option value="lost">Lost</option>
            <option value="pending">Pending</option>
            <option value="cancelled">Cancelled</option>
            <option value="unknown">Unknown</option>
          </select>
        </div>

        <div className="space-y-2">
          <label htmlFor="helpfulness_score" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Helpfulness Score *
          </label>
          <select
            id="helpfulness_score"
            value={formData.helpfulness_score}
            onChange={(e) => setFormData({ ...formData, helpfulness_score: Number(e.target.value) as FeedbackSubmitPayload['helpfulness_score'] })}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
          >
            <option value={1}>1 - Not helpful</option>
            <option value={2}>2 - Slightly helpful</option>
            <option value={3}>3 - Moderately helpful</option>
            <option value={4}>4 - Very helpful</option>
            <option value={5}>5 - Extremely helpful</option>
          </select>
        </div>

        <div className="space-y-2">
          <label htmlFor="bid_price" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Bid Price (BDT) *
          </label>
          <input
            id="bid_price"
            type="number"
            value={formData.bid_price || ''}
            onChange={(e) => setFormData({ ...formData, bid_price: Number(e.target.value) || 0 })}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
            placeholder="Enter bid price"
          />
          {errors.bid_price && (
            <p className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />
              {errors.bid_price}
            </p>
          )}
        </div>

        <div className="space-y-2 md:col-span-2">
          <label htmlFor="notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Notes
          </label>
          <textarea
            id="notes"
            value={formData.notes || ''}
            onChange={(e) => setFormData({ ...formData, notes: e.target.value || undefined })}
            rows={4}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
            placeholder="Enter your feedback, concerns, or suggestions..."
          />
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          disabled={submitFeedbackMutation.isPending}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 flex items-center gap-2"
          disabled={submitFeedbackMutation.isPending}
        >
          {submitFeedbackMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          Submit Feedback
        </button>
      </div>
    </form>
  )
}