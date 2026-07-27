import { useState, createContext, useContext, useRef, useEffect, type ReactNode } from 'react'
import { cn } from '../lib/cn'

interface SelectContextValue {
  value: string
  onValueChange: (value: string) => void
  open: boolean
  setOpen: (open: boolean) => void
}

const SelectContext = createContext<SelectContextValue>({ value: '', onValueChange: () => {}, open: false, setOpen: () => {} })

interface SelectProps {
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  children: ReactNode
}

export function Select({ value: controlledValue, defaultValue, onValueChange, children }: SelectProps) {
  const [internal, setInternal] = useState(defaultValue ?? controlledValue ?? '')
  const [open, setOpen] = useState(false)
  const value = controlledValue ?? internal
  const setValue = onValueChange ?? setInternal

  return (
    <SelectContext.Provider value={{ value, onValueChange: setValue, open, setOpen }}>
      <div className="relative inline-block">{children}</div>
    </SelectContext.Provider>
  )
}

export function SelectTrigger({ className, children, ...props }: { className?: string; children?: ReactNode }) {
  const { open, setOpen } = useContext(SelectContext)
  return (
    <button
      type="button"
      onClick={() => setOpen(!open)}
      className={cn(
        'flex h-10 w-full items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}

export function SelectValue({ placeholder }: { placeholder?: string }) {
  const { value } = useContext(SelectContext)
  if (!value) return <span className="text-gray-400">{placeholder ?? 'Select...'}</span>
  return <span>{value}</span>
}

export function SelectContent({ className, children, ...props }: { className?: string; children: ReactNode }) {
  const { open, setOpen } = useContext(SelectContext)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open, setOpen])

  if (!open) return null

  return (
    <div
      ref={ref}
      className={cn(
        'absolute z-50 mt-1 w-full min-w-[12rem] rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function SelectItem({ value, className, children, ...props }: { value: string; className?: string; children: ReactNode }) {
  const { value: selectedValue, onValueChange, setOpen } = useContext(SelectContext)
  const isSelected = selectedValue === value

  return (
    <button
      type="button"
      onClick={() => { onValueChange(value); setOpen(false) }}
      className={cn(
        'w-full px-3 py-2 text-left text-sm transition-colors hover:bg-gray-100 dark:hover:bg-gray-800',
        isSelected && 'bg-brand-50 font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
