// Environment variable type definitions for Vite
interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_PORT: string
  readonly VITE_HOST: string
  readonly VITE_ENABLE_DEMO_MODE: string
  readonly VITE_ENABLE_SSO: string
  readonly VITE_SSO_TENANT_ID: string
  readonly VITE_OIDC_IDP_ID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
