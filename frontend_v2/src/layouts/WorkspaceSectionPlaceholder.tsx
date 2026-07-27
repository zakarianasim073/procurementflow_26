import { ScreenTemplate } from './ScreenTemplate'

export interface WorkspaceSectionPlaceholderProps {
  title: string
  description: string
  /** Which PFX ticket(s) build this section's real content. */
  builtIn: string
}

/**
 * Stand-in for a workspace section whose real content hasn't been built yet (Phases 4-9).
 * Renders through ScreenTemplate so routing/nav can be fully wired and clicked through in
 * PFX-05 without waiting for every later ticket. Each route using this is replaced by its
 * real feature implementation in the ticket named in `builtIn`.
 */
export function WorkspaceSectionPlaceholder({ title, description, builtIn }: WorkspaceSectionPlaceholderProps) {
  return (
    <ScreenTemplate
      header={
        <>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">{title}</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
        </>
      }
      primary={
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">
          Built in {builtIn}.
        </div>
      }
    />
  )
}
