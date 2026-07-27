import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Menu } from 'lucide-react'
import { findWorkspaceForPath } from '@shared/navigation/workspaces'
import { WorkspaceNav } from './navigation/WorkspaceNav'

/**
 * Overall app chrome: WorkspaceNav (sidebar/rail/drawer) + header (mobile hamburger,
 * breadcrumb) + <Outlet /> for the active route's screen. One level up from ScreenTemplate,
 * which handles the per-screen slot layout inside <Outlet />.
 */
export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const location = useLocation()

  const activeWorkspace = findWorkspaceForPath(location.pathname)
  const activeSection = activeWorkspace?.sections.find((s) => s.path === location.pathname)

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-950">
      <WorkspaceNav drawerOpen={drawerOpen} onCloseDrawer={() => setDrawerOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b border-gray-200 bg-white px-4 dark:border-gray-800 dark:bg-gray-900">
          <button
            type="button"
            className="md:hidden"
            aria-label="Open navigation"
            onClick={() => setDrawerOpen(true)}
          >
            <Menu size={20} />
          </button>

          <nav aria-label="Breadcrumb" className="text-sm text-gray-500 dark:text-gray-400">
            {activeWorkspace ? (
              <span>
                {activeWorkspace.label}
                {activeSection && activeSection.id !== 'overview' ? ` / ${activeSection.label}` : ''}
              </span>
            ) : (
              <span>ProcureFlow</span>
            )}
          </nav>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
