import { Copy, FileText, Link, Star } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

interface ContextMenuAction {
  label: string
  icon: React.ReactNode
  action: () => void
}

interface ClauseTreeContextMenuProps {
  ruleId: string
  ruleLabel: string
  position?: { x: number; y: number }
  onClose?: () => void
}

export function ClauseTreeContextMenu({
  ruleId,
  ruleLabel,
  position,
  onClose,
}: ClauseTreeContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose?.()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  const actions: ContextMenuAction[] = [
    {
      label: 'Copy Rule ID',
      icon: <Copy className="h-4 w-4" />,
      action: () => {
        navigator.clipboard.writeText(ruleId)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      },
    },
    {
      label: 'View Detail',
      icon: <FileText className="h-4 w-4" />,
      action: () => console.log('Navigate to detail'),
    },
    {
      label: 'Related Clauses',
      icon: <Link className="h-4 w-4" />,
      action: () => console.log('Show related'),
    },
    {
      label: 'Bookmark',
      icon: <Star className="h-4 w-4" />,
      action: () => console.log('Bookmarked'),
    },
  ]

  return (
    <div
      ref={menuRef}
      className="fixed z-50 min-w-48 rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800"
      style={{
        top: position?.y ? `${position.y}px` : 'auto',
        left: position?.x ? `${position.x}px` : 'auto',
      }}
    >
      <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <p className="text-xs font-semibold text-gray-900 dark:text-white truncate">{ruleLabel}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">{ruleId}</p>
      </div>

      <div className="py-1">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={() => {
              action.action()
              onClose?.()
            }}
            className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-900/50 transition-colors"
          >
            {action.icon}
            <span>{action.label}</span>
            {action.label === 'Copy Rule ID' && copied && (
              <span className="ml-auto text-xs text-green-600 dark:text-green-400">✓</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
