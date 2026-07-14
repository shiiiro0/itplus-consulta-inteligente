import type { Configuration, PublicClientApplication } from '@azure/msal-browser'

const env = (import.meta as unknown as { env: Record<string, string | undefined> }).env

const clientId = env.VITE_AZURE_CLIENT_ID
const tenantId = env.VITE_AZURE_TENANT_ID
const redirectUri = env.VITE_AZURE_REDIRECT_URI || window.location.origin

export const isAzureEnabled = Boolean(clientId && tenantId)

const config: Configuration = {
  auth: {
    clientId: clientId ?? '',
    authority: `https://login.microsoftonline.com/${tenantId ?? 'common'}`,
    redirectUri,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
}

const loginRequest = { scopes: ['User.Read', 'openid', 'profile', 'email'], prompt: 'select_account' }

let msalInstance: PublicClientApplication | null = null
let initialized = false

async function ensureInit(): Promise<PublicClientApplication> {
  if (!msalInstance) {
    const { PublicClientApplication } = await import('@azure/msal-browser')
    msalInstance = new PublicClientApplication(config)
  }
  if (!initialized) {
    await msalInstance.initialize()
    initialized = true
  }
  return msalInstance
}

export async function azureLogin(): Promise<string> {
  if (!isAzureEnabled) {
    throw new Error('El inicio de sesión con Microsoft no está configurado.')
  }
  const msal = await ensureInit()
  const result = await msal.loginPopup(loginRequest)
  if (!result.idToken) {
    throw new Error('Microsoft no devolvió un token de identidad.')
  }
  return result.idToken
}

export async function azureLogout(): Promise<void> {
  if (!isAzureEnabled) return
  try {
    const msal = await ensureInit()
    await msal.clearCache()
  } catch {
    /* noop */
  }
}
