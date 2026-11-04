import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../src/App'
import { AuthContext } from '../src/auth/AuthContext'
import type { AuthContextValue } from '../src/auth/AuthContext'
import { ApiError } from '../src/api/client'
import type { User } from '../src/api/client'

function mount(request: AuthContextValue['request'], role: 'USER' | 'ADMIN' = 'ADMIN') {
  const auth: AuthContextValue = { user: { id: 1, username: 'admin', role, is_blocked: false },
    signIn: async () => undefined, signOut: () => undefined, register: async () => undefined,
    getToken: () => 'token', request }
  render(<MemoryRouter initialEntries={['/admin']}><AuthContext.Provider value={auth}><App /></AuthContext.Provider></MemoryRouter>)
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('administration', () => {
  it('shows aggregate statistics and blocks/unblocks users after confirmation', async () => {
    let blocked = false
    const request = vi.fn(async (path: string, init?: RequestInit) => {
      if (path.startsWith('/admin/users?')) return [
        { id: 1, username: 'admin', role: 'ADMIN', is_blocked: false },
        { id: 2, username: 'person', role: 'USER', is_blocked: blocked },
      ]
      if (path.startsWith('/admin/statistics?')) return { year: 2026, month: 11, total_users: 2, blocked_users: blocked ? 1 : 0, total_transactions: 5, monthly_transactions: 2, total_savings_goals: 1, custom_categories: 3 }
      if (path === '/admin/users/2/block' && init?.method === 'PATCH') { blocked = true; return { id: 2, username: 'person', role: 'USER', is_blocked: true } }
      if (path === '/admin/users/2/unblock' && init?.method === 'PATCH') { blocked = false; return { id: 2, username: 'person', role: 'USER', is_blocked: false } }
      throw new Error(`Unexpected ${path}`)
    }) as AuthContextValue['request']
    mount(request)
    await screen.findByText('person')
    expect((screen.getByRole('button', { name: 'Заблокировать пользователя admin' }) as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText('Все операции').nextElementSibling?.textContent).toBe('5')
    await userEvent.click(screen.getByRole('button', { name: 'Заблокировать пользователя person' }))
    let dialog = screen.getByRole('alertdialog')
    expect(dialog.textContent).toContain('не сможет войти')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Отмена' }))
    expect(vi.mocked(request).mock.calls.some(([path]) => path.endsWith('/block'))).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Заблокировать пользователя person' }))
    dialog = screen.getByRole('alertdialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Заблокировать' }))
    await screen.findByText('Пользователь заблокирован.')
    const unblock = await screen.findByRole('button', { name: 'Разблокировать пользователя person' })
    await waitFor(() => expect((unblock as HTMLButtonElement).disabled).toBe(false))
    await userEvent.click(unblock)
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Разблокировать' }))
    expect(await screen.findByText('Пользователь разблокирован.')).toBeTruthy()
    await waitFor(() => expect(screen.getByText('Заблокированы').nextElementSibling?.textContent).toBe('0'))
  })

  it('changes statistics period and paginates users', async () => {
    const request = vi.fn(async (path: string) => {
      if (path.startsWith('/admin/statistics?')) return { year: 2025, month: 1, total_users: 26, blocked_users: 0, total_transactions: 0, monthly_transactions: 0, total_savings_goals: 0, custom_categories: 0 }
      if (path.includes('skip=25')) return [{ id: 26, username: 'last', role: 'USER', is_blocked: false }]
      if (path.startsWith('/admin/users?')) return Array.from({ length: 25 }, (_, i): User => ({ id: i + 1, username: `user-${i + 1}`, role: 'USER', is_blocked: false }))
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount(request)
    await screen.findByText('user-1 (вы)')
    await userEvent.click(screen.getByRole('button', { name: 'Далее' }))
    await screen.findByText('last')
    expect(screen.getByText('Страница 2')).toBeTruthy()
    await userEvent.clear(screen.getByLabelText('Месяц'))
    await userEvent.type(screen.getByLabelText('Месяц'), '2025-01')
    await waitFor(() => expect(vi.mocked(request).mock.calls.some(([path]) => path === '/admin/statistics?year=2025&month=1')).toBe(true))
  })

  it('shows errors and does not open the page for an ordinary user', async () => {
    const request = vi.fn(async (path: string) => {
      if (path.startsWith('/admin/users?')) throw new ApiError(403, 'Доступ запрещён')
      if (path.startsWith('/admin/statistics?')) throw new ApiError(500, 'Ошибка статистики')
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount(request)
    expect((await screen.findAllByRole('alert')).map(item => item.textContent).join(' ')).toContain('Доступ запрещён')
    expect(screen.getByText(/Ошибка статистики/)).toBeTruthy()
    cleanup(); vi.mocked(request).mockClear()
    mount(request, 'USER')
    expect(screen.getByRole('heading', { name: 'Доступ запрещён' })).toBeTruthy()
    expect(request).not.toHaveBeenCalled()
  })

  it('keeps the confirmation open when blocking fails', async () => {
    const request = vi.fn(async (path: string) => {
      if (path.startsWith('/admin/users?')) return [{ id: 2, username: 'person', role: 'USER', is_blocked: false }]
      if (path.startsWith('/admin/statistics?')) return { year: 2026, month: 11, total_users: 1, blocked_users: 0, total_transactions: 0, monthly_transactions: 0, total_savings_goals: 0, custom_categories: 0 }
      if (path === '/admin/users/2/block') throw new ApiError(403, 'Действие запрещено')
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount(request)
    await screen.findByText('person')
    await userEvent.click(screen.getByRole('button', { name: 'Заблокировать пользователя person' }))
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Заблокировать' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Действие запрещено')
    expect(screen.getByRole('alertdialog')).toBeTruthy()
  })
})
