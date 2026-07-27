import { type ReactNode } from 'react'
import { cn } from '@shared/lib/cn'
import { EmptyState } from '@shared/ui/EmptyState'

export interface Column<T = unknown> {
  id: string
  header: string
  accessor: (row: T) => ReactNode
  sortable?: boolean
  align?: 'left' | 'center' | 'right'
  width?: string
}

interface WidgetTableProps<T> {
  columns: Column<T>[]
  data: T[]
  onRowClick?: (row: T) => void
  className?: string
  emptyMessage?: string
  loading?: boolean
}

export function WidgetTable<T extends { id?: string | number }>({
  columns,
  data,
  onRowClick,
  className,
  emptyMessage = 'No data available',
  loading,
}: WidgetTableProps<T>) {
  if (loading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <div className="flex flex-col items-center gap-2 text-gray-400">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-brand-500" />
          <span className="text-xs">Loading...</span>
        </div>
      </div>
    )
  }

  if (!data.length) {
    return (
      <div className={cn('p-8', className)}>
        <EmptyState title={emptyMessage} />
      </div>
    )
  }

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-gray-100 dark:border-gray-800">
            {columns.map((col) => (
              <th
                key={col.id}
                className={cn(
                  'px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400',
                  col.align === 'right' && 'text-right',
                  col.align === 'center' && 'text-center',
                )}
                style={col.width ? { width: col.width } : undefined}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={row.id ?? i}
              onClick={() => onRowClick?.(row)}
              className={cn(
                'border-b border-gray-50 transition-colors last:border-0 dark:border-gray-800/50',
                onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/30' : '',
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.id}
                  className={cn(
                    'px-4 py-2.5 text-gray-700 dark:text-gray-300',
                    col.align === 'right' && 'text-right',
                    col.align === 'center' && 'text-center',
                  )}
                >
                  {col.accessor(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
