import { useRef, useState } from 'react'

const DOCUMENT_TYPES = [
  { value: 'boq', label: 'Bill of Quantities (BOQ)' },
  { value: 'tds', label: 'Tender Data Sheet (TDS)' },
  { value: 'notice', label: 'Tender Notice' },
  { value: 'specification', label: 'Specification' },
  { value: 'drawing', label: 'Drawing' },
  { value: 'other', label: 'Other' },
]

interface Props {
  tenderId: string
  onUpload: (file: File, docType: string) => void
  isLoading?: boolean
  isExpanded?: boolean
  onToggle?: () => void
}

export function DocumentUploadPanel({ onUpload, isLoading, isExpanded = false, onToggle }: Props) {
  const [selectedType, setSelectedType] = useState('boq')
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(e.type === 'dragenter' || e.type === 'dragover')
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      const file = files[0]
      if (file.type === 'application/pdf' || file.type.includes('spreadsheet') || file.type.includes('word')) {
        onUpload(file, selectedType)
      } else {
        alert('Please upload PDF, Excel, or Word documents only')
      }
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      onUpload(files[0], selectedType)
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800"
      >
        <span className="font-medium text-gray-900 dark:text-white">Upload Document</span>
        <span className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`}>▼</span>
      </button>

      {isExpanded && (
        <div className="border-t border-gray-200 p-4 dark:border-gray-800">
          <div className="space-y-3">
            {/* Document Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Document Type
              </label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                disabled={isLoading}
                className="w-full rounded border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800 disabled:opacity-50"
              >
                {DOCUMENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Drag and Drop Area */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`relative rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
                dragActive
                  ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-900/20'
                  : 'border-gray-300 dark:border-gray-600'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileSelect}
                disabled={isLoading}
                className="hidden"
                accept=".pdf,.xlsx,.xls,.docx,.doc"
              />

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                className="mx-auto flex flex-col items-center gap-2 disabled:opacity-50"
              >
                <span className="text-2xl">📄</span>
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {isLoading ? 'Uploading...' : 'Drag file here or click to select'}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    PDF, Excel, or Word documents (max 50MB)
                  </p>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
