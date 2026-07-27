import { useState, createContext, useContext, type ReactNode, type HTMLAttributes } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '../lib/cn'

interface AccordionContextValue {
  expandedItems: Set<string>
  toggle: (id: string) => void
  type: 'single' | 'multiple'
}

const AccordionContext = createContext<AccordionContextValue>({ expandedItems: new Set(), toggle: () => {}, type: 'multiple' })

const ItemIdContext = createContext<string>('')

export interface AccordionProps extends HTMLAttributes<HTMLDivElement> {
  type?: 'single' | 'multiple'
  defaultValue?: string[]
  children: ReactNode
}

export function Accordion({ type = 'multiple', defaultValue = [], children, className, ...props }: AccordionProps) {
  const [expanded, setExpanded] = useState(new Set(defaultValue))

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(type === 'single' ? [] : prev)
      if (prev.has(id)) {
        if (type !== 'single') next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  return (
    <AccordionContext.Provider value={{ expandedItems: expanded, toggle, type }}>
      <div className={cn('divide-y divide-gray-200 dark:divide-gray-800', className)} {...props}>
        {children}
      </div>
    </AccordionContext.Provider>
  )
}

export interface AccordionItemProps extends HTMLAttributes<HTMLDivElement> {
  id: string
  children: ReactNode
}

export function AccordionItem({ id, className, children, ...props }: AccordionItemProps) {
  const ctx = useContext(AccordionContext)
  const isOpen = ctx.expandedItems.has(id)

  return (
    <ItemIdContext.Provider value={id}>
      <div className={cn('py-0', className)} data-state={isOpen ? 'open' : 'closed'} {...props}>
        {children}
      </div>
    </ItemIdContext.Provider>
  )
}

export interface AccordionTriggerProps extends HTMLAttributes<HTMLButtonElement> {
  children: ReactNode
}

export function AccordionTrigger({ className, children, ...props }: AccordionTriggerProps) {
  const ctx = useContext(AccordionContext)
  const itemId = useContext(ItemIdContext)
  const isOpen = ctx.expandedItems.has(itemId)

  return (
    <button
      type="button"
      aria-expanded={isOpen}
      onClick={() => ctx.toggle(itemId)}
      className={cn(
        'flex w-full items-center justify-between py-3 text-sm font-medium text-gray-900 dark:text-white',
        'hover:text-gray-600 dark:hover:text-gray-300 transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded-md',
        className,
      )}
      {...props}
    >
      {children}
      <ChevronDown className={cn('h-4 w-4 shrink-0 text-gray-400 transition-transform', isOpen && 'rotate-180')} />
    </button>
  )
}

export interface AccordionContentProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

export function AccordionContent({ className, children, ...props }: AccordionContentProps) {
  const ctx = useContext(AccordionContext)
  const itemId = useContext(ItemIdContext)
  const isOpen = ctx.expandedItems.has(itemId)

  if (!isOpen) return null

  return (
    <div className="overflow-hidden text-sm text-gray-600 dark:text-gray-400" {...props}>
      <div className={cn('pb-3', className)}>{children}</div>
    </div>
  )
}
