import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getMe, login as apiLogin, loginAzure as apiLoginAzure } from '../api/auth'
import { clearAuth, getStoredUser, getToken, setAuth } from '../api/client'
import { azureLogout } from '../auth/msalConfig'

interface UserInfo {
  username: string
  email: string
  rol: string
  permisos: string[]
  nombre?: string
}

interface AuthContextValue {
  user: UserInfo | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  loginWithAzure: (token: string) => Promise<void>
  logout: () => void
  isAdmin: boolean
  can: (modulo: string) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

const ADMIN_ONLY_FALLBACK = ['usuarios', 'roles', 'sesiones']

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [isLoading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    const stored = getStoredUser()
    if (!token || !stored) {
      setLoading(false)
      return
    }
    setUser({ ...stored, permisos: stored.permisos ?? [] })
    getMe()
      .then((me) => {
        const info: UserInfo = {
          username: me.username,
          email: me.email,
          nombre: me.nombre,
          rol: me.rol,
          permisos: me.permisos ?? [],
        }
        setAuth(token, info)
        setUser(info)
      })
      .catch(() => clearAuth())
      .finally(() => setLoading(false))
  }, [])

  const persist = (info: UserInfo, token: string) => {
    setAuth(token, info)
    setUser(info)
  }

  const login = useCallback(async (username: string, password: string) => {
    const resp = await apiLogin(username, password)
    persist(
      {
        username: resp.username,
        email: resp.email,
        rol: resp.rol,
        permisos: resp.permisos ?? [],
      },
      resp.access_token,
    )
  }, [])

  const loginWithAzure = useCallback(async (token: string) => {
    const resp = await apiLoginAzure(token)
    persist(
      {
        username: resp.username,
        email: resp.email,
        rol: resp.rol,
        permisos: resp.permisos ?? [],
      },
      resp.access_token,
    )
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setUser(null)
    void azureLogout()
  }, [])

  const isAdmin = (user?.rol ?? '').trim().toLowerCase() === 'administrador'

  const can = useCallback(
    (modulo: string): boolean => {
      if (isAdmin) return true
      const permisos = user?.permisos ?? []
      if (permisos.length > 0) return permisos.includes(modulo)
      return !ADMIN_ONLY_FALLBACK.includes(modulo)
    },
    [isAdmin, user],
  )

  return (
    <AuthContext.Provider
      value={{ user, isLoading, login, loginWithAzure, logout, isAdmin, can }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
