import { useLocation } from 'react-router-dom'
import { findWorkspaceForPath } from '@shared/navigation/workspaces'
import { WorkspaceSwitcher } from './WorkspaceSwitcher'
import { WorkspaceSectionList } from './WorkspaceSectionList'

export interface WorkspaceNavProps {
  /** Controls the <768px drawer overlay; ignored at >=768px where the nav is always visible. */
  drawerOpen: boolean
  onCloseDrawer: () => void
}

/**
 * Full workspace navigation: WorkspaceSwitcher + the active workspace's WorkspaceSectionList.
 * Responsive per docs/frontend/07_NAVIGATION.md: full sidebar >=1024px, icon rail 768-1024px,
 * drawer overlay <768px.
 */
export function WorkspaceNav({ drawerOpen, onCloseDrawer }: WorkspaceNavProps) {
  const location = useLocation()
  const activeWorkspace = findWorkspaceForPath(location.pathname)

  const content = (
    <div className="flex h-full w-64 flex-col gap-6 overflow-y-auto border-r border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900 lg:w-56 md:w-16 md:items-center">
      <div className="px-2 md:hidden">
        <span className="bg-brand-gradient bg-clip-text text-lg font-extrabold text-transparent">
          ProcureFlow
        </span>
      </div>

      <div className="md:w-full">
        <WorkspaceSwitcher compact={false} />
      </div>

      {/* Section list only makes sense with labels — hidden at the icon-rail breakpoint. */}
      <div className="hidden lg:block">
        <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {activeWorkspace.label}
        </p>
        <WorkspaceSectionList workspace={activeWorkspace} />
      </div>
    </div>
  )

  return (
    <>
      {/* >=768px: always visible, collapses to icon rail below 1024px via the classes above. */}
      <div className="hidden md:block">{content}</div>

      {/* <768px: drawer overlay. */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button
            type="button"
            aria-label="Close navigation"
            onClick={onCloseDrawer}
            className="absolute inset-0 bg-black/40"
          />
          <div className="relative h-full">{content}</div>
        </div>
      )}
    </>
  )
}
