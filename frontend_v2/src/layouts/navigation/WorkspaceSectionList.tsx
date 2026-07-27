import { useRef, type KeyboardEvent } from 'react'
import { NavLink } from 'react-router-dom'
import clsx from 'clsx'
import type { Workspace } from '@shared/index'
import { useWorkspacePermissions } from '@shared/index'

export interface WorkspaceSectionListProps {
  workspace: Workspace
}

/**
 * Section list for the currently active workspace. Roving tabindex within this group,
 * independent from WorkspaceSwitcher's group (Tab moves between the two).
 * Sections with `requiresPermission` are hidden unless useWorkspacePermissions grants it —
 * see docs/frontend/07_NAVIGATION.md "Security".
 */
export function WorkspaceSectionList({ workspace }: WorkspaceSectionListProps) {
  const { hasPermission } = useWorkspacePermissions()
  const visibleSections = workspace.sections.filter(
    (section) => !section.requiresPermission || hasPermission(section.requiresPermission)
  )
  const itemRefs = useRef<Array<HTMLAnchorElement | null>>([])

  const handleKeyDown = (index: number) => (e: KeyboardEvent<HTMLAnchorElement>) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    const delta = e.key === 'ArrowDown' ? 1 : -1
    const next = (index + delta + visibleSections.length) % visibleSections.length
    itemRefs.current[next]?.focus()
  }

  if (visibleSections.length === 0) return null

  return (
    <nav aria-label={`${workspace.label} sections`} className="space-y-0.5 pl-1">
      {visibleSections.map((section, index) => (
        <NavLink
          key={section.id}
          to={section.path}
          end={section.path === workspace.path}
          ref={(el) => {
            itemRefs.current[index] = el
          }}
          tabIndex={index === 0 ? 0 : -1}
          onKeyDown={handleKeyDown(index)}
          onFocus={(e) => {
            itemRefs.current.forEach((el) => el?.setAttribute('tabindex', '-1'))
            e.currentTarget.setAttribute('tabindex', '0')
          }}
          className={({ isActive }) =>
            clsx(
              'block rounded-lg px-2 py-1.5 text-sm transition',
              isActive
                ? 'bg-brand-50 font-semibold text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
            )
          }
        >
          {section.label}
        </NavLink>
      ))}
    </nav>
  )
}
