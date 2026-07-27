import { useState } from 'react'
import { ScreenTemplate } from '@layouts/index'
import { useDocumentList, useDocumentUpload } from '@hooks/index'
import { DocumentUploadPanel } from './DocumentUploadPanel'
import { DocumentList } from './DocumentList'
import { useTenderBrainDetail } from '@hooks/tender'

export function DocumentsPage() {
  const [selectedTenderId, setSelectedTenderId] = useState<string>('')
  const [expandedPanel, setExpandedPanel] = useState(false)

  const { data: tenderDetail } = useTenderBrainDetail(selectedTenderId)
  const { data: documentList, isLoading } = useDocumentList({
    tender_id: selectedTenderId,
    skip: 0,
    limit: 50,
  })
  const { mutate: uploadDocument, isPending: isUploading } = useDocumentUpload()

  const handleUpload = async (file: File, docType: string) => {
    if (!selectedTenderId) {
      alert('Please select a tender first')
      return
    }

    uploadDocument(
      { tenderId: selectedTenderId, file, docType },
      {
        onSuccess: () => {
          setExpandedPanel(false)
          alert('Document uploaded successfully')
        },
        onError: (error) => {
          alert(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
        },
      },
    )
  }

  return (
    <ScreenTemplate
      header={
        <>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Document Management</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Upload and extract data from tender documents
          </p>
        </>
      }
      primary={
        <div className="space-y-4">
          {/* Tender Selection */}
          <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select Tender
            </label>
            <input
              type="text"
              placeholder="Enter tender ID..."
              value={selectedTenderId}
              onChange={(e) => setSelectedTenderId(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800"
            />
            {tenderDetail && (
              <div className="mt-3 text-sm text-gray-600 dark:text-gray-400">
                <p>
                  <strong>{tenderDetail.tender.title}</strong>
                </p>
                <p className="text-xs">{tenderDetail.tender.agency}</p>
              </div>
            )}
          </div>

          {selectedTenderId ? (
            <>
              {/* Upload Panel */}
              <DocumentUploadPanel
                tenderId={selectedTenderId}
                onUpload={handleUpload}
                isLoading={isUploading}
                isExpanded={expandedPanel}
                onToggle={() => setExpandedPanel(!expandedPanel)}
              />

              {/* Document List */}
              <DocumentList
                documents={documentList ?? []}
                isLoading={isLoading}
                tenderId={selectedTenderId}
              />
            </>
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8 text-center dark:border-gray-600 dark:bg-gray-900">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Select a tender to view and upload documents
              </p>
            </div>
          )}
        </div>
      }
    />
  )
}
