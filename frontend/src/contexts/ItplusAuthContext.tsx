import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import {
  clearItplusAuth,
  getItplusToken,
  getItplusUser,
  itplusGetMe,
  itplusLogin,
  setItplusAuth,
} from '../api/itplus'

interface ItplusUser {
  email: string
  role: string
}

interface ItplusAuthContextValue {
  user: ItplusUser | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const ItplusAuthContext = createContext<ItplusAuthContextValue | null>(null)

export function ItplusAuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<ItplusUser | null>(null)
  const [isLoading, setLoading] = useState(true)

  useEffect(() => {
    const token = getItplusToken()
    const stored = getItplusUser()
    if (!token || !stored) {
      setLoading(false)
      return
    }
    setUser(stored)
    itplusGetMe()
      .then((me) => {
        const info = { email: me.email, role: me.role }
        setItplusAuth(token, info)
        setUser(info)
      })
      .catch(() => clearItplusAuth())
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const resp = await itplusLogin(email, password)
    setItplusAuth(resp.access_token, { email, role: 'user' })
    const me = await itplusGetMe()
    const info = { email: me.email, role: me.role }
    setItplusAuth(resp.access_token, info)
    setUser(info)
  }, [])

  const logout = useCallback(() => {
    clearItplusAuth()
    setUser(null)
  }, [])

  return (
    <ItplusAuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </ItplusAuthContext.Provider>
  )
}

export function useItplusAuth() {
  const ctx = useContext(ItplusAuthContext)
  if (!ctx) throw new Error('useItplusAuth must be used within ItplusAuthProvider')
  return ctx
}
