import { createContext, useContext } from 'react'
import type { User } from '../api/client'

export interface AuthContextValue {
  user: User | null
  signIn: (username: string, password: string) => Promise<void>
  signOut: () => void
  register: (username: string, password: string) => Promise<void>
  getToken: () => string | null
  request: <T>(path: string, init?: RequestInit) => Promise<T>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth requires AuthProvider')
  return context
}
