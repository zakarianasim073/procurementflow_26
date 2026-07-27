let _token: string | null =
  typeof window !== 'undefined' ? window.localStorage.getItem('pf_access_token') : null

export function setAuthToken(token: string) {
  _token = token
  if (typeof window !== 'undefined') {
    window.localStorage.setItem('pf_access_token', token)
  }
}

export function getAuthToken(): string | null {
  return _token
}

export function clearAuthToken() {
  _token = null
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem('pf_access_token')
  }
}

export function getTenantId(): string | null {
  if (!_token) return null
  try {
    const payload = _token.split('.')[1]
    const decoded = JSON.parse(atob(payload))
    return decoded.tenant_id ?? null
  } catch {
    return null
  }
}
