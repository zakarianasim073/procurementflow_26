/** Return only same-origin application paths suitable for React Router navigation. */
export function safeInternalPath(candidate: string | null | undefined, fallback = '/executive'): string {
  if (!candidate || !candidate.startsWith('/') || candidate.startsWith('//') || candidate.includes('\\')) {
    return fallback
  }
  try {
    const parsed = new URL(candidate, window.location.origin)
    if (parsed.origin !== window.location.origin) return fallback
    return `${parsed.pathname}${parsed.search}${parsed.hash}`
  } catch {
    return fallback
  }
}
