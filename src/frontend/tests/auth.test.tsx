import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../src/App'
import { AuthProvider } from '../src/auth/AuthProvider'
import { useAuth } from '../src/auth/AuthContext'

const token = `header.${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))}.signature`
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })

function mount(path = '/transactions') {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><App /></AuthProvider></MemoryRouter>)
}

async function fillLogin() {
  await userEvent.type(screen.getByLabelText('Логин'), 'demo-user')
  await userEvent.type(screen.getByLabelText('Пароль'), 'password123')
  await userEvent.click(screen.getByRole('button', { name: 'Войти' }))
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  localStorage.clear()
  sessionStorage.clear()
})

describe('authentication', () => {
  it('redirects a guest, signs in using OAuth form and keeps the token in memory', async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      if (input === '/api/auth/login') {
        expect(init?.body).toBeInstanceOf(URLSearchParams)
        const form = init?.body
        if (!(form instanceof URLSearchParams)) throw new Error('Expected form-encoded credentials')
        expect(form.get('username')).toBe('demo-user')
        return json({ access_token: token, token_type: 'bearer' })
      }
      if (input === '/api/auth/me') {
        expect(new Headers(init?.headers).get('Authorization')).toBe(`Bearer ${token}`)
        return json({ id: 10, username: 'demo-user', role: 'USER', is_blocked: false })
      }
      throw new Error(`Unexpected request ${input}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    mount('/categories')
    expect(screen.getByRole('heading', { name: 'С возвращением' })).toBeTruthy()
    await fillLogin()
    await screen.findByRole('heading', { name: 'Категории' })
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
    expect(screen.queryByRole('link', { name: 'Администрирование' })).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'Выйти' }))
    expect(await screen.findByRole('heading', { name: 'С возвращением' })).toBeTruthy()
  })

  it('shows login errors and never enters a protected route', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ detail: 'Неверный логин или пароль' }, 401)))
    mount()
    await fillLogin()
    expect((await screen.findByRole('alert')).textContent).toContain('Неверный логин или пароль')
    expect(screen.getByRole('heading', { name: 'С возвращением' })).toBeTruthy()
  })

  it('registers and prompts the user to log in', async () => {
    const fetchMock = vi.fn(async () => json({ id: 1, username: 'new-user', role: 'USER', is_blocked: false }, 201))
    vi.stubGlobal('fetch', fetchMock)
    mount('/register')
    await userEvent.type(screen.getByLabelText('Логин'), 'new-user')
    await userEvent.type(screen.getByLabelText('Пароль', { exact: true }), 'password123')
    await userEvent.type(screen.getByLabelText('Повторите пароль'), 'password123')
    await userEvent.click(screen.getByRole('button', { name: 'Создать аккаунт' }))
    expect((await screen.findByRole('status')).textContent).toContain('Аккаунт создан')
    expect(fetchMock).toHaveBeenCalledOnce()
  })

  it('hides the admin route from users and allows an admin', async () => {
    let role = 'USER'
    vi.stubGlobal('fetch', vi.fn(async (input: string | URL | Request) => input === '/api/auth/login'
      ? json({ access_token: token, token_type: 'bearer' })
      : json({ id: 1, username: 'demo-user', role, is_blocked: false })))
    const first = mount('/admin')
    await fillLogin()
    expect(await screen.findByRole('heading', { name: 'Доступ запрещён' })).toBeTruthy()
    first.unmount()
    role = 'ADMIN'
    mount('/admin')
    await fillLogin()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Администрирование' })).toBeTruthy())
    expect(screen.getByRole('link', { name: 'Администрирование' })).toBeTruthy()
  })

  it('clears the session if a protected request returns 401', async () => {
    function Probe() {
      const { user, signIn, request } = useAuth()
      return <>{user ? <button onClick={() => { void request('/transactions/').catch(() => undefined) }}>Запрос</button>
        : <button onClick={() => { void signIn('demo-user', 'password123') }}>Вход</button>}</>
    }
    vi.stubGlobal('fetch', vi.fn(async (input: string | URL | Request) => {
      if (input === '/api/auth/login') return json({ access_token: token, token_type: 'bearer' })
      if (input === '/api/auth/me') return json({ id: 1, username: 'demo-user', role: 'USER', is_blocked: false })
      return json({ detail: 'Токен истёк' }, 401)
    }))
    render(<AuthProvider><Probe /></AuthProvider>)
    await userEvent.click(screen.getByRole('button', { name: 'Вход' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Запрос' }))
    expect(await screen.findByRole('button', { name: 'Вход' })).toBeTruthy()
  })

  it('distinguishes role restrictions from a blocked account', async () => {
    function Probe() {
      const { user, signIn, request } = useAuth()
      return <>{user ? <button onClick={() => { void request('/admin/users').catch(() => undefined) }}>Запрос</button>
        : <button onClick={() => { void signIn('demo-user', 'password123') }}>Вход</button>}</>
    }
    let blocked = false
    vi.stubGlobal('fetch', vi.fn(async (input: string | URL | Request) => {
      if (input === '/api/auth/login') return json({ access_token: token, token_type: 'bearer' })
      if (input === '/api/auth/me') return blocked ? json({ detail: 'Заблокирован' }, 403)
        : json({ id: 1, username: 'demo-user', role: 'USER', is_blocked: false })
      return json({ detail: 'Доступ запрещён' }, 403)
    }))
    render(<AuthProvider><Probe /></AuthProvider>)
    await userEvent.click(screen.getByRole('button', { name: 'Вход' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Запрос' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Запрос' })).toBeTruthy())
    blocked = true
    await userEvent.click(screen.getByRole('button', { name: 'Запрос' }))
    expect(await screen.findByRole('button', { name: 'Вход' })).toBeTruthy()
  })
})
