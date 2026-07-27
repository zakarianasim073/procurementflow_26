import { useState, createContext, useContext, useEffect, useRef, useCallback, type ReactNode, type HTMLAttributes } from 'react'
import { X } from 'lucide-react'
import { cn } from '../lib/cn'

interface DialogContextValue {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const DialogContext = createContext<DialogContextValue>({ open: false, onOpenChange: () => {} })

export interface DialogProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  defaultOpen?: boolean
  children: ReactNode
}

export function Dialog({ open: controlledOpen, onOpenChange, defaultOpen = false, children }: DialogProps) {
  const [internal, setInternal] = useState(defaultOpen)
  const open = controlledOpen ?? internal
  const setOpen = onOpenChange ?? setInternal

  return (
    <DialogContext.Provider value={{ open, onOpenChange: setOpen }}>{children}</DialogContext.Provider>
  )
}

export function DialogTrigger({ children, ...props }: HTMLAttributes<HTMLButtonElement>) {
  const ctx = useContext(DialogContext)
  return (
    <button type="button" onClick={() => ctx.onOpenChange(true)} {...props}>
      {children}
    </button>
  )
}

export function DialogContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  const ctx = useContext(DialogContext)
  const overlayRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') ctx.onOpenChange(false)
  }, [ctx])

  useEffect(() => {
    if (!ctx.open) return
    document.addEventListener('keydown', handleEscape)
    document.body.style.overflow = 'hidden'
    panelRef.current?.focus()
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [ctx.open, handleEscape])

  if (!ctx.open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        ref={overlayRef}
        className="absolute inset-0 bg-black/50"
        onClick={() => ctx.onOpenChange(false)}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        className={cn(
          'relative z-10 w-full max-w-lg rounded-xl border border-gray-200 bg-white p-6 shadow-xl',
          'dark:border-gray-800 dark:bg-gray-900',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
          'max-h-[85vh] overflow-y-auto',
          className,
        )}
        {...props}
      >
        {children}
      </div>
    </div>
  )
}

export function DialogHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mb-4 flex flex-col gap-1', className)} {...props} />
}

export function DialogTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-lg font-semibold text-gray-900 dark:text-white', className)} {...props} />
}

export function DialogDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-gray-500 dark:text-gray-400', className)} {...props} />
}

export function DialogBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('text-sm text-gray-700 dark:text-gray-300', className)} {...props} />
}

export function DialogFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mt-6 flex justify-end gap-3', className)} {...props} />
}

export function DialogClose({ className, ...props }: HTMLAttributes<HTMLButtonElement>) {
  const ctx = useContext(DialogContext)
  return (
    <button
      type="button"
      onClick={() => ctx.onOpenChange(false)}
      className={cn(
        'absolute right-4 top-4 rounded-md p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        className,
      )}
      aria-label="Close"
      {...props}
    >
      <X size={16} />
    </button>
  )
}
