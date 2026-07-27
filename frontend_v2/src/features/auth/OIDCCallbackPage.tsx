import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AlertCircle, Loader2 } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import { setAuthToken } from '@entities/authToken'

export function OIDCCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [error, setError] = useState<string>('')
  const [isProcessing, setIsProcessing] = useState(true)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const error_param = searchParams.get('error')

        if (error_param) {
          setError(`Authentication failed: ${error_param}`)
          setIsProcessing(false)
          return
        }

        if (!code) {
          setError('Missing authorization code from OIDC provider')
          setIsProcessing(false)
          return
        }

        // Exchange code for token
        const tenantId = import.meta.env.VITE_SSO_TENANT_ID
        if (!tenantId) {
          setError('SSO tenant configuration is missing')
          setIsProcessing(false)
          return
        }
        const response = await fetch(`/api/v2/sso/oidc/callback?tenant_id=${encodeURIComponent(tenantId)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, state: state || '' }),
        })

        if (!response.ok) {
          const errorData = await response.json()
          setError(errorData.detail || 'Failed to exchange authorization code')
          setIsProcessing(false)
          return
        }

        const data = await response.json()

        // Store token and user info
        if (data.access_token) {
          setAuthToken(data.access_token)
          if (data.refresh_token) {
            localStorage.setItem('pf_refresh_token', data.refresh_token)
          }

          // Redirect to dashboard or original page
          const referrer = sessionStorage.getItem('auth_referrer') || '/executive'
          sessionStorage.removeItem('auth_referrer')
          navigate(referrer)
        } else {
          setError('No token received from server')
          setIsProcessing(false)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error during authentication')
        setIsProcessing(false)
      }
    }

    handleCallback()
  }, [searchParams, navigate])

  if (isProcessing) {
    return (
      <ScreenTemplate
        header={
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Signing you in...</h1>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Please wait while we authenticate your account</p>
          </div>
        }
        primary={
          <div className="flex items-center justify-center py-12">
            <Loader2 size={48} className="animate-spin text-blue-600" />
          </div>
        }
      />
    )
  }

  if (error) {
    return (
      <ScreenTemplate
        header={
          <div className="text-center">
            <h1 className="text-2xl font-bold text-red-900 dark:text-red-300">Authentication Error</h1>
          </div>
        }
        primary={
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950/30">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
              <div>
                <h2 className="font-semibold text-red-900 dark:text-red-300">{error}</h2>
                <p className="mt-2 text-sm text-red-800 dark:text-red-400">
                  Please try logging in again or contact support if the problem persists.
                </p>
                <button
                  onClick={() => navigate('/login')}
                  className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-600"
                >
                  Back to Login
                </button>
              </div>
            </div>
          </div>
        }
      />
    )
  }

  return null
}
