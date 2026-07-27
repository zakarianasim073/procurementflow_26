/**
 * Placeholder for the pre-workspace auth routes (/login, /sso/oidc/callback, /sso/saml/callback).
 * These render outside AppShell (no sidebar — the user isn't authenticated yet) and keep their
 * exact frontend/ path unchanged, so no legacy redirect is needed for them. Real implementation
 * (ported from frontend/src/pages/LoginPage.tsx etc.) lands in PFX-25.
 */
export function AuthPlaceholder({ title }: {
    title: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
      <div className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">
        <p className="mb-1 font-medium text-gray-700 dark:text-gray-300">{title}</p>
        <p>Built in PFX-25.</p>
      </div>
    </div>
  )
}
