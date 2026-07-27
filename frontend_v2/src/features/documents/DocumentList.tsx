import { useDocumentExtraction } from '@hooks/index'
import type { DocumentMetadata } from '@entities/documents'

interface Props {
  documents: DocumentMetadata[]
  isLoading?: boolean
  tenderId: string
}

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200',
  processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
}

const DOC_TYPE_LABELS: Record<string, string> = {
  boq: 'Bill of Quantities',
  tds: 'Tender Data Sheet',
  notice: 'Tender Notice',
  specification: 'Specification',
  drawing: 'Drawing',
  other: 'Other',
}

export function DocumentList({ documents, isLoading }: Props) {
  const { mutate: extractDocument, isPending: isExtracting } = useDocumentExtraction()

  const handleExtract = (documentId: string) => {
    extractDocument(documentId, {
      onSuccess: () => {
        alert('Extraction started - check status updates')
      },
      onError: (error) => {
        alert(`Extraction failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
      },
    })
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 rounded-lg border border-gray-200 bg-gray-50 animate-pulse dark:border-gray-800 dark:bg-gray-800"
          />
        ))}
      </div>
    )
  }

  if (!documents || documents.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8 text-center dark:border-gray-600 dark:bg-gray-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">No documents uploaded yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <h3 className="font-semibold text-gray-900 dark:text-white">
        Uploaded Documents ({documents.length})
      </h3>
      <div className="space-y-2">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">📄</span>
                  <p className="font-medium text-gray-900 dark:text-white truncate">{doc.name}</p>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>{DOC_TYPE_LABELS[doc.document_type] || doc.document_type}</span>
                  <span>•</span>
                  <span>{(doc.file_size / 1024 / 1024).toFixed(2)} MB</span>
                  <span>•</span>
                  <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Status Badge */}
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
                    STATUS_COLORS[doc.extraction_status] || STATUS_COLORS.pending
                  }`}
                >
                  {doc.extraction_status === 'processing' && '⏳ '}
                  {doc.extraction_status === 'completed' && '✓ '}
                  {doc.extraction_status === 'failed' && '✗ '}
                  {doc.extraction_status.charAt(0).toUpperCase() + doc.extraction_status.slice(1)}
                </span>

                {/* Extract Button */}
                {doc.extraction_status === 'pending' && (
                  <button
                    onClick={() => handleExtract(doc.id)}
                    disabled={isExtracting}
                    className="px-3 py-1 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {isExtracting ? 'Processing...' : 'Extract'}
                  </button>
                )}

                <span className="text-xs text-gray-400 dark:text-gray-500" title={doc.file_path}>
                  {doc.mime_type}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
