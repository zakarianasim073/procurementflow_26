import { getAuthToken, setAuthToken } from './authToken'

let bootstrapPromise: Promise<void> | null = null

function hasUsableToken(): boolean {
  const token = getAuthToken()
  if (!token) return false
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return typeof payload.exp === 'number' && payload.exp * 1000 > Date.now() + 60_000
  } catch {
    return false
  }
}

/**
 * Establish the configured local owner session once per page load.
 *
 * The full-stack launcher supplies these Vite variables for the local owner
 * deployment. Re-authenticating here replaces expired/stale JWTs before
 * React Query starts protected API calls. Deployments without configured
 * owner credentials continue to use the explicit login flow.
 */
export function bootstrapAuth(): Promise<void> {
  if (bootstrapPromise) return bootstrapPromise

  if (import.meta.env.MODE === 'test') {
    bootstrapPromise = Promise.resolve()
    return bootstrapPromise
  }

  if (hasUsableToken()) {
    bootstrapPromise = Promise.resolve()
    return bootstrapPromise
  }

  const email = import.meta.env.VITE_OWNER_EMAIL
  const password = import.meta.env.VITE_OWNER_PASSWORD
  if (!email || !password) {
    bootstrapPromise = Promise.resolve()
    return bootstrapPromise
  }

  bootstrapPromise = fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Owner bootstrap login failed with HTTP ${response.status}`)
      }
      const data = await response.json()
      if (!data.access_token) throw new Error('Owner bootstrap login returned no access token')
      setAuthToken(data.access_token)
      if (data.refresh_token && typeof window !== 'undefined') {
        window.localStorage.setItem('pf_refresh_token', data.refresh_token)
      }
    })
    .catch((error) => {
      bootstrapPromise = null
      throw error
    })

  return bootstrapPromise
}

/**
 * Protected API calls share the same bootstrap promise so they cannot race
 * the owner login during initial application render.
 */
export function authReady(): Promise<void> {
  return bootstrapAuth()
}
