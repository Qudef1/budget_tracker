import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { ApiError, apiRequest, authApi } from '../api/client'
import type { User } from '../api/client'
import { AuthContext } from './AuthContext'

// This is used only for clearing the local session promptly; the server verifies the token.
function expiresAt(token: string): number | null {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const decoded: unknown = JSON.parse(atob(payload))
    return decoded && typeof decoded === 'object' && 'exp' in decoded && typeof decoded.exp === 'number'
      ? decoded.exp * 1000 : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const currentToken = useRef<string | null>(null)
  const generation = useRef(0)

  const signOut = useCallback(() => {
    generation.current += 1
    currentToken.current = null
    setToken(null)
    setUser(null)
  }, [])

  const signIn = useCallback(async (username: string, password: string) => {
    const attempt = ++generation.current
    const result = await authApi.login(username, password)
    const profile = await authApi.me(result.access_token)
    if (attempt !== generation.current) return
    currentToken.current = result.access_token
    setToken(result.access_token)
    setUser(profile)
  }, [])

  const register = useCallback(async (username: string, password: string) => {
    await authApi.register(username, password)
  }, [])

  const getToken = useCallback(() => currentToken.current, [])

  const request = useCallback(async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
    const accessToken = currentToken.current
    if (!accessToken) throw new ApiError(401, 'Войдите, чтобы продолжить.')
    const headers = new Headers(init.headers)
    headers.set('Authorization', `Bearer ${accessToken}`)
    try {
      return await apiRequest<T>(path, { ...init, headers })
    } catch (error) {
      if (currentToken.current === accessToken && error instanceof ApiError) {
        if (error.status === 401) signOut()
        // A 403 might be a role restriction, not a blocked account. Check /me before logging out.
        if (error.status === 403) {
          try {
            await authApi.me(accessToken)
          } catch (profileError) {
            if (currentToken.current === accessToken && profileError instanceof ApiError &&
                (profileError.status === 401 || profileError.status === 403)) signOut()
          }
        }
      }
      throw error
    }
  }, [signOut])

  useEffect(() => {
    if (!token) return
    const expiry = expiresAt(token)
    if (expiry === null) return
    let timer = 0
    const schedule = () => {
      const delay = expiry - Date.now()
      if (delay <= 0) signOut()
      else timer = window.setTimeout(schedule, Math.min(delay, 2_147_483_647))
    }
    schedule()
    return () => window.clearTimeout(timer)
  }, [token, signOut])

  useEffect(() => {
    if (!token) return
    const validate = async () => {
      if (document.visibilityState !== 'visible') return
      try {
        const profile = await authApi.me(token)
        if (currentToken.current === token) setUser(profile)
      } catch (error) {
        if (currentToken.current === token && error instanceof ApiError && (error.status === 401 || error.status === 403)) signOut()
      }
    }
    document.addEventListener('visibilitychange', validate)
    return () => document.removeEventListener('visibilitychange', validate)
  }, [token, signOut])

  return <AuthContext.Provider value={{ user, signIn, signOut, register, getToken, request }}>{children}</AuthContext.Provider>
}
