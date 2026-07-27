import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Loader2 } from 'lucide-react'
import { ScreenTemplate } from '@layouts/index'
import { setAuthToken } from '@entities/authToken'

export function SAMLCallbackPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<string>('')
  const [isProcessing, setIsProcessing] = useState(true)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // SAML response is typically sent via POST
        // The browser will auto-submit a form from the IdP
        // We need to extract the assertion from the form data or hidden field

        // Check if there's a SAMLResponse in the document
        const samlResponseElement = document.querySelector('input[name="SAMLResponse"]') as HTMLInputElement
        const relayStateElement = document.querySelector('input[name="RelayState"]') as HTMLInputElement

        if (!samlResponseElement) {
          setError('No SAML assertion found in authentication response')
          setIsProcessing(false)
          return
        }

        const samlResponse = samlResponseElement.value
        const relayState = relayStateElement?.value

        // Send SAML response to backend for processing
        const tenantId = import.meta.env.VITE_SSO_TENANT_ID
        if (!tenantId) {
          setError('SSO tenant configuration is missing')
          setIsProcessing(false)
          return
        }
        const response = await fetch(`/api/v2/sso/saml/acs?tenant_id=${encodeURIComponent(tenantId)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ saml_response: samlResponse, relay_state: relayState }),
        })

        if (!response.ok) {
          const errorData = await response.json()
          setError(errorData.detail || 'Failed to process SAML assertion')
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
          const referrer = relayState || sessionStorage.getItem('auth_referrer') || '/executive'
          sessionStorage.removeItem('auth_referrer')
          navigate(referrer)
        } else {
          setError('No token received from server')
          setIsProcessing(false)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error during SAML authentication')
        setIsProcessing(false)
      }
    }

    // Give the browser time to render hidden form fields
    const timer = setTimeout(handleCallback, 100)
    return () => clearTimeout(timer)
  }, [navigate])

  if (isProcessing) {
    return (
      <ScreenTemplate
        header={
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Processing SAML Authentication...</h1>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Please wait while we verify your identity</p>
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
            <h1 className="text-2xl font-bold text-red-900 dark:text-red-300">SAML Authentication Error</h1>
          </div>
        }
        primary={
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950/30">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
              <div>
                <h2 className="font-semibold text-red-900 dark:text-red-300">{error}</h2>
                <p className="mt-2 text-sm text-red-800 dark:text-red-400">
                  There was an issue processing your SAML assertion. Please try again or contact support.
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
