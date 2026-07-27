/**
 * Placeholder permission check for nav filtering (ADR-006 security note on PFX-05).
 *
 * frontend_v2 has no auth store yet (built in PFX-25/26). Until then this permits every
 * permission key so nothing in the nav is incorrectly hidden during early development.
 * PFX-26 replaces the body of this hook with a real check against the RBAC-backed auth
 * store — the shape (`hasPermission(key): boolean`) is fixed now so WorkspaceNav's call
 * sites don't need to change later.
 *
 * IMPORTANT: this is a UX convenience only. Hiding a nav item here must never be the only
 * thing protecting a route — the backend must independently 403 unauthorized requests to
 * the same endpoint regardless of what the nav shows.
 */
export function useWorkspacePermissions() {
  function hasPermission(_permissionKey: string): boolean {
    return true
  }

  return { hasPermission }
}
