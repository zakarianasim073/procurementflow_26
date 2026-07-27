import { getAuthToken } from './authToken'
import { authReady } from './bootstrapAuth'

export interface FetchJsonOptions {
  method?: string
  body?: string | FormData
  headers?: Record<string, string>
  authed?: boolean
}

export async function fetchJson<T>(url: string, options?: FetchJsonOptions | boolean): Promise<T> {
  // Application APIs are protected by the global backend auth middleware.
  // Defaulting to anonymous requests made otherwise healthy widgets silently
  // render zero/empty states on HTTP 401. Public callers can still opt out
  // explicitly with { authed: false }.
  let authed = true
  let init: RequestInit = {}

  if (typeof options === 'boolean') {
    authed = options
  } else if (options) {
    authed = options.authed ?? true
    init = {
      method: options.method,
      body: options.body as BodyInit | undefined,
      headers: options.headers,
    }
  }

  const headers: Record<string, string> = {}
  if (!(options as FetchJsonOptions)?.body || (options as FetchJsonOptions)?.body instanceof FormData) {
    // Don't set Content-Type for FormData (browser sets multipart boundary)
  } else {
    headers['Content-Type'] = 'application/json'
  }
  if (authed) {
    await authReady()
    const token = getAuthToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  init.headers = { ...headers, ...(init.headers as Record<string, string> | undefined) }

  const res = await fetch(url, init)
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.json()
}
