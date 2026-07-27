import { Link } from 'react-router-dom'
import { ScreenTemplate } from './ScreenTemplate'

/**
 * Renders for any unmatched route — via ScreenTemplate so it looks like a real workspace
 * screen (header + primary only) rather than a blank page. See docs/frontend/07_NAVIGATION.md
 * "404 handling".
 */
export function NotFoundScreen() {
  return (
    <ScreenTemplate
      header={<h1 className="text-xl font-semibold text-gray-900 dark:text-white">Page not found</h1>}
      primary={
        <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900">
          <p className="mb-3">That page doesn&apos;t exist, or has moved.</p>
          <Link to="/executive" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
            Go to the Executive workspace
          </Link>
        </div>
      }
    />
  )
}
