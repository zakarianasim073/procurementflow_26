export interface DocumentListParams {
  tender_id?: string
  doc_type?: string
  skip?: number
  limit?: number
}

/** Matches backend DocumentResponse (app/api/v2/documents.py) */
export interface DocumentMetadata {
  id: string
  name: string
  document_type: string
  tender_id: string
  file_path: string
  file_size: number
  mime_type: string
  extraction_status: 'pending' | 'processing' | 'completed' | 'failed'
  extracted_data?: Record<string, unknown> | null
  created_at: string
  updated_at: string
  created_by: string
}

/** POST /documents/{id}/extract */
export interface DocumentExtractionResponse {
  status: string
  document_id: string
  extracted_data?: Record<string, unknown>
}
