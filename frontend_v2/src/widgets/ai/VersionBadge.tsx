import { cn } from '@shared/lib/cn'

export interface VersionBadgeProps {
  version: string
  createdAt?: string
  className?: string
}

export function VersionBadge({ version, createdAt, className }: VersionBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400',
        className,
      )}
      title={createdAt ? `Version ${version} — ${new Date(createdAt).toLocaleString()}` : `Version ${version}`}
    >
      v{version}
    </span>
  )
}
