import { createContext } from 'react'

export type ToastVariant = 'success' | 'error' | 'warning' | 'info'

export interface ToastItem {
  id: string
  variant: ToastVariant
  title: string
  description?: string
}

export interface ToastContextValue {
  toasts: ToastItem[]
  addToast: (variant: ToastVariant, title: string, description?: string) => void
  dismissToast: (id: string) => void
}

export const ToastContext = createContext<ToastContextValue>({ toasts: [], addToast: () => {}, dismissToast: () => {} })
