import { useState, useCallback, useEffect, type ReactNode } from 'react'
import { X } from 'lucide-react'
import clsx from 'clsx'
import { cn } from '../lib/cn'
import { ToastContext, type ToastItem, type ToastVariant } from './ToastContext'

export interface ToastProps {
  id: string
  variant?: ToastVariant
  title: string
  description?: string
  onDismiss: (id: string) => void
}

const variantStyles: Record<ToastVariant, string> = {
  success: 'border-success-300 bg-success-50 dark:border-success-700 dark:bg-success-950/40',
  error: 'border-danger-300 bg-danger-50 dark:border-danger-700 dark:bg-danger-950/40',
  warning: 'border-warning-300 bg-warning-50 dark:border-warning-700 dark:bg-warning-950/40',
  info: 'border-info-300 bg-info-50 dark:border-info-700 dark:bg-info-950/40',
}

const iconStyles: Record<ToastVariant, string> = {
  success: 'bg-success-700 text-white dark:bg-success-300 dark:text-success-950',
  error: 'bg-danger-700 text-white dark:bg-danger-300 dark:text-danger-950',
  warning: 'bg-warning-700 text-white dark:bg-warning-300 dark:text-warning-950',
  info: 'bg-info-700 text-white dark:bg-info-300 dark:text-info-950',
}

const iconMap: Record<ToastVariant, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'i',
}

export function Toast({ id, variant = 'info', title, description, onDismiss }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), 5000)
    return () => clearTimeout(timer)
  }, [id, onDismiss])

  return (
    <div
      role="alert"
      className={cn(
        'pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border p-4 shadow-lg',
        'transition-all animate-in slide-in-from-right-full',
        variantStyles[variant],
      )}
    >
      <span className={clsx('mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold', iconStyles[variant])}>
        {iconMap[variant]}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-white">{title}</p>
        {description && <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{description}</p>}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(id)}
        className="shrink-0 rounded-md p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
    </div>
  )
}

let toastCounter = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const addToast = useCallback((variant: ToastVariant, title: string, description?: string) => {
    const id = `toast-${++toastCounter}`
    setToasts((prev) => [...prev, { id, variant, title, description }])
  }, [])

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, dismissToast }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <Toast key={t.id} {...t} onDismiss={dismissToast} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}
