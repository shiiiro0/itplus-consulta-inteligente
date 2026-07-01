import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { clearAuth, getMe, getStoredUser, getToken, login as apiLogin, setAuth } from '../api/client'

interface User {
  email: string
  role: string
}

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    const stored = getStoredUser()
    if (!token || !stored) {
      setLoading(false)
      return
    }
    setUser(stored)
    getMe()
      .then((me) => {
        const info = { email: me.email, role: me.role }
        setAuth(token, info)
        setUser(info)
      })
      .catch(() => clearAuth())
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const resp = await apiLogin(email, password)
    setAuth(resp.access_token, { email, role: 'user' })
    const me = await getMe()
    const info = { email: me.email, role: me.role }
    setAuth(resp.access_token, info)
    setUser(info)
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
