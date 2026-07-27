export interface Submission {
  submission_id: string
  tender_id: string
  tender_title: string
  agency: string
  status: 'draft' | 'preparing' | 'ready' | 'submitted' | 'under_review' | 'accepted' | 'rejected'
  deadline: string
  submitted_at?: string
  documents: SubmissionDocument[]
  notes?: string
  created_at: string
  updated_at: string
}

export interface SubmissionDocument {
  document_id: string
  name: string
  type: string
  uploaded_at: string
  size: number
}

export interface SubmissionTimeline {
  submission_id: string
  events: SubmissionEvent[]
}

export interface SubmissionEvent {
  event_id: string
  action: string
  user: string
  timestamp: string
  details?: string
}
