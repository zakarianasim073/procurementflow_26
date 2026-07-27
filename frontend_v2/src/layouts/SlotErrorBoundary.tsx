import { Component, type ReactNode } from 'react'

interface Props {
  /** Already bound to this slot's name by the caller (see ScreenTemplate's `handleError`). */
  onError?: (error: Error) => void
  children: ReactNode
}

interface State {
  error: Error | null
}

/**
 * Wraps a single ScreenTemplate slot so a crash inside it degrades that slot
 * only — the rest of the screen (and its other slots) keeps rendering.
 * See docs/frontend/06_LAYOUT_SYSTEM.md "Error state".
 */
export class SlotErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error) {
    this.props.onError?.(error)
  }

  render() {
    if (this.state.error) {
      return (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
        >
          This section couldn&apos;t load.
        </div>
      )
    }
    return this.props.children
  }
}
