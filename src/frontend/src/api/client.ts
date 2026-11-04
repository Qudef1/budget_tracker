export type UserRole = 'USER' | 'ADMIN'

export interface User {
  id: number
  username: string
  role: UserRole
  is_blocked: boolean
}

interface TokenResponse {
  access_token: string
  token_type: 'bearer'
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, init)
  } catch {
    throw new ApiError(0, 'Не удалось связаться с сервером. Проверьте подключение и попробуйте снова.')
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    throw new ApiError(response.status, typeof detail === 'string' ? detail : 'Не удалось выполнить запрос.')
  }
  if (response.status === 204) return undefined as T
  return await response.json() as T
}

export const authApi = {
  register(username: string, password: string) {
    return apiRequest<User>('/auth/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
  },
  login(username: string, password: string) {
    return apiRequest<TokenResponse>('/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
    })
  },
  me(token: string) {
    return apiRequest<User>('/auth/me', { headers: { Authorization: `Bearer ${token}` } })
  },
}
