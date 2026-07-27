import { useRef, type KeyboardEvent } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import {
  LayoutDashboard, Radar, FileText, ShieldCheck, BookOpen, Building2, Settings, type LucideIcon,
} from 'lucide-react'
import { findWorkspaceForPath, WORKSPACES } from '@shared/navigation/workspaces'

const ICONS: Record<string, LucideIcon> = {
  LayoutDashboard, Radar, FileText, ShieldCheck, BookOpen, Building2, Settings,
}

export interface WorkspaceSwitcherProps {
  /** Icon-only rail (768-1024px) vs full labeled list (>=1024px). */
  compact?: boolean
}

/**
 * Top-level workspace switcher: one entry per workspace in WORKSPACES.
 * Roving tabindex within this group — arrow keys move focus, Tab leaves the group entirely.
 * See docs/frontend/07_NAVIGATION.md "Keyboard navigation".
 */
export function WorkspaceSwitcher({ compact = false }: WorkspaceSwitcherProps) {
  const itemRefs = useRef<Array<HTMLAnchorElement | null>>([])
  const location = useLocation()
  const activeWorkspace = findWorkspaceForPath(location.pathname)

  const handleKeyDown = (index: number) => (e: KeyboardEvent<HTMLAnchorElement>) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    const delta = e.key === 'ArrowDown' ? 1 : -1
    const next = (index + delta + WORKSPACES.length) % WORKSPACES.length
    itemRefs.current[next]?.focus()
  }

  return (
    <nav aria-label="Workspaces" className="space-y-1">
      {WORKSPACES.map((workspace, index) => {
        const Icon = ICONS[workspace.icon] ?? LayoutDashboard
        return (
          <NavLink
            key={workspace.id}
            to={workspace.path}
            ref={(el) => {
              itemRefs.current[index] = el
            }}
            tabIndex={index === 0 ? 0 : -1}
            onKeyDown={handleKeyDown(index)}
            onFocus={(e) => {
              // Roving tabindex: whichever item is focused becomes the group's tab stop.
              itemRefs.current.forEach((el) => el?.setAttribute('tabindex', '-1'))
              e.currentTarget.setAttribute('tabindex', '0')
            }}
            className={() =>
              clsx(
                'flex items-center gap-3 rounded-lg px-2 py-2 text-sm font-medium transition',
                compact && 'justify-center px-0',
                // bg-interactive (solid brand-600), not bg-brand-gradient: PFX-06's contrast
                // audit found white text fails AA at every stop of the gradient.
                activeWorkspace.id === workspace.id
                  ? 'bg-interactive text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
              )
            }
          >
            <Icon size={18} aria-hidden="true" />
            {!compact && <span>{workspace.label}</span>}
          </NavLink>
        )
      })}
    </nav>
  )
}
