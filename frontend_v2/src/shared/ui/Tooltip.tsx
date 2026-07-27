import { useState, useRef, type ReactNode, type HTMLAttributes } from 'react'
import { cn } from '../lib/cn'

export interface TooltipProps extends Omit<HTMLAttributes<HTMLDivElement>, 'content'> {
  content: ReactNode
  side?: 'top' | 'bottom' | 'left' | 'right'
  delayMs?: number
  children: ReactNode
}

export function Tooltip({ content, side = 'top', delayMs = 300, children, className }: TooltipProps) {
  const [visible, setVisible] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const show = () => {
    timerRef.current = setTimeout(() => setVisible(true), delayMs)
  }
  const hide = () => {
    clearTimeout(timerRef.current)
    setVisible(false)
  }

  const positionStyles = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }

  const id = `tooltip-${Math.random().toString(36).slice(2, 8)}`

  return (
    <div
      className={cn('relative inline-flex', className)}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      aria-describedby={visible ? id : undefined}
    >
      {children}
      {visible && (
        <div
          id={id}
          role="tooltip"
          className={cn(
            'pointer-events-none absolute z-50 whitespace-nowrap rounded-md px-2.5 py-1 text-xs font-medium',
            'bg-gray-900 text-white dark:bg-gray-700 dark:text-gray-100',
            'shadow-md',
            positionStyles[side],
          )}
        >
          {content}
        </div>
      )}
    </div>
  )
}
