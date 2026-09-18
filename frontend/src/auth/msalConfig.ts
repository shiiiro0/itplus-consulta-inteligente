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
    // clearCache() solo borraba el cache local de MSAL — la sesión SSO en
    // Microsoft (la cookie de login.microsoftonline.com) seguía activa, así
    // que un siguiente "Iniciar sesión con Microsoft" en el mismo navegador
    // volvía a autenticar sin pedir credenciales, sin importar que la app
    // hubiera "cerrado sesión". logoutPopup() sí termina la sesión en el
    // proveedor (y de paso también limpia el cache local).
    const account = msal.getActiveAccount() ?? msal.getAllAccounts()[0]
    await msal.logoutPopup({ account, mainWindowRedirectUri: window.location.origin })
  } catch {
    // Si el popup fue bloqueado o el usuario lo cerró, no bloqueamos el
    // logout local por esto — AuthContext ya limpió el token/estado propio.
  }
}
