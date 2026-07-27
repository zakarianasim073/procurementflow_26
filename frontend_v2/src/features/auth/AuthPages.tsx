import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Bot, Loader2 } from 'lucide-react'
import { Button } from '@shared/ui/Button'
import { Input } from '@shared/ui/Input'
import { Card } from '@shared/ui/Card'
import { setAuthToken } from '@entities/authToken'
import { safeInternalPath } from '@shared/lib/safeNavigation'

const apiBaseUrl = import.meta.env.VITE_API_URL?.replace(/\/$/, '') ?? ''

interface LoginFormData {
  email: string
  password: string
}

export function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const redirectTo = safeInternalPath(searchParams.get('redirect'))

  const [formData, setFormData] = useState<LoginFormData>({ email: '', password: '' })
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const ssoTenantId = import.meta.env.VITE_SSO_TENANT_ID
  const oidcIdpId = import.meta.env.VITE_OIDC_IDP_ID
  const oidcEnabled = import.meta.env.VITE_ENABLE_SSO === 'true' && Boolean(ssoTenantId && oidcIdpId)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Login failed')
      }

      const data = await response.json()
      setAuthToken(data.access_token)
      localStorage.setItem('pf_refresh_token', data.refresh_token)
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleOidcLogin() {
    setError(null)
    try {
      const params = new URLSearchParams({
        idp_id: oidcIdpId,
        tenant_id: ssoTenantId,
      })
      const response = await fetch(`/api/v2/sso/oidc/init?${params}`, { method: 'POST' })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'SSO initialization failed')
      }
      const data = await response.json()
      window.location.assign(data.authorization_url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'SSO initialization failed')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
      <Card className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-4 p-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-900/40">
            <Bot className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="text-center">
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">ProcureFlow</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Sign in to your account</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-6 pt-0">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400" role="alert">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Email
            </label>
            <Input
              id="email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData((prev) => ({ ...prev, email: e.target.value }))}
              placeholder="you@company.com"
              required
              autoComplete="email"
              aria-describedby={error ? 'login-error' : undefined}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Password
            </label>
            <Input
              id="password"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData((prev) => ({ ...prev, password: e.target.value }))}
              placeholder="Enter your password"
              required
              autoComplete="current-password"
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isLoading || !formData.email || !formData.password}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in...
              </>
            ) : (
              'Sign in'
            )}
          </Button>
        </form>

        {oidcEnabled && <div className="border-t border-gray-200 p-4 dark:border-gray-800">
          <p className="text-center text-xs text-gray-500 dark:text-gray-400">
            Or sign in with SSO
          </p>
          <div className="mt-3">
            <Button variant="secondary" className="w-full" onClick={handleOidcLogin}>
              OIDC
            </Button>
          </div>
        </div>}
      </Card>
    </div>
  )
}

export function OidcCallbackPage() {
  const [searchParams] = useSearchParams()
  const code = searchParams.get('code')
  const error = searchParams.get('error')

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
        <Card className="w-full max-w-sm p-6 text-center">
          <div className="mb-4 text-red-500">
            <Bot className="mx-auto h-12 w-12" />
          </div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">SSO Login Failed</h1>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            The OIDC provider returned an error. Please try again or contact your administrator.
          </p>
          <Button className="mt-4" onClick={() => window.location.href = '/login'}>
            Return to Login
          </Button>
        </Card>
      </div>
    )
  }

  if (!code) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
        <Card className="w-full max-w-sm p-6 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-500" />
          <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Processing authentication...</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
      <Card className="w-full max-w-sm p-6 text-center">
        <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-500" />
        <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Completing sign-in...</p>
      </Card>
    </div>
  )
}

export function SamlCallbackPage() {
  const [searchParams] = useSearchParams()
  const error = searchParams.get('error')

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
        <Card className="w-full max-w-sm p-6 text-center">
          <div className="mb-4 text-red-500">
            <Bot className="mx-auto h-12 w-12" />
          </div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">SAML Login Failed</h1>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            The SAML provider returned an error. Please try again or contact your administrator.
          </p>
          <Button className="mt-4" onClick={() => window.location.href = '/login'}>
            Return to Login
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
      <Card className="w-full max-w-sm p-6 text-center">
        <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-500" />
        <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Processing SAML authentication...</p>
      </Card>
    </div>
  )
}
