import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../src/App'
import { AuthContext } from '../src/auth/AuthContext'
import type { AuthContextValue } from '../src/auth/AuthContext'
import { ApiError } from '../src/api/client'
import type { BudgetLimit, SavingsGoal } from '../src/api/finance'

function mount(path: string, request: AuthContextValue['request']) {
  const auth: AuthContextValue = { user: { id: 1, username: 'test', role: 'USER', is_blocked: false },
    signIn: async () => undefined, signOut: () => undefined, register: async () => undefined,
    getToken: () => 'token', request }
  render(<MemoryRouter initialEntries={[path]}><AuthContext.Provider value={auth}><App /></AuthContext.Provider></MemoryRouter>)
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('budgets', () => {
  it('creates, updates, shows execution and history, and archives a limit', async () => {
    let limits: BudgetLimit[] = []
    const execution = { limit_id: 7, year: 2026, month: 11, month_limit: '100.00', expense_amount: '85.00', usage_percent: '85.00', period_status: 'warning', warning: true, exceeded: false }
    const request = vi.fn(async (path: string, init?: RequestInit) => {
      if (path.startsWith('/categories/')) return [{ id: 1, name: 'Еда', transaction_type: 'expense', category_type: 'custom', month_limit: 1000 }, { id: 2, name: 'Зарплата', transaction_type: 'income', category_type: 'custom', month_limit: 1000 }]
      if (path.startsWith('/budgets/limits?')) return [...limits]
      if (path === '/budgets/limits' && init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        expect(body).toEqual({ amount: '100.00', category_id: 1, currency: 'BYN' })
        limits = [{ id: 7, user_id: 1, ...body }]; return limits[0]
      }
      if (path === '/budgets/limits/7' && init?.method === 'PATCH') {
        expect(JSON.parse(String(init.body))).toEqual({ amount: '150' })
        limits = [{ ...limits[0], amount: '150' }]; return limits[0]
      }
      if (path === '/budgets/limits/7' && init?.method === 'DELETE') { limits = []; return undefined }
      if (path.includes('/execution?')) return execution
      if (path === '/budgets/limits/7/history') return [execution]
      throw new Error(`Unexpected ${path}`)
    }) as AuthContextValue['request']
    mount('/budgets', request)
    await screen.findByText('Лимитов пока нет.')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить лимит' }))
    expect(within(screen.getByLabelText('Категория расходов')).queryByText('Зарплата')).toBeNull()
    await userEvent.selectOptions(screen.getByLabelText('Категория расходов'), '1')
    await userEvent.type(screen.getByLabelText('Сумма лимита'), '100,00')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    expect(await screen.findByText('Больше 80% лимита', { exact: false })).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'История лимита 7' }))
    expect(await screen.findByText('11.2026')).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'Изменить лимит 7' }))
    await userEvent.clear(screen.getByLabelText('Сумма лимита'))
    await userEvent.type(screen.getByLabelText('Сумма лимита'), '150')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await screen.findByText('Лимит изменён.')
    await userEvent.click(screen.getByRole('button', { name: 'Удалить лимит 7' }))
    const dialog = screen.getByRole('alertdialog')
    expect(dialog.textContent).toContain('история сохранится')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Удалить лимит' }))
    await screen.findByText(/Лимит №7 архивирован/)
    await userEvent.click(screen.getByRole('button', { name: 'Показать историю' }))
    expect(await screen.findByText('11.2026')).toBeTruthy()
  })

  it('shows duplicate limit errors', async () => {
    const request = vi.fn(async (path: string, init?: RequestInit) => {
      if (path.startsWith('/categories/')) return [{ id: 1, name: 'Еда', transaction_type: 'expense', category_type: 'custom', month_limit: 1000 }]
      if (path.startsWith('/budgets/limits?')) return []
      if (init?.method === 'POST') throw new ApiError(409, 'Лимит уже существует')
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount('/budgets', request)
    await screen.findByText('Лимитов пока нет.')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить лимит' }))
    await userEvent.selectOptions(screen.getByLabelText('Категория расходов'), '1')
    await userEvent.type(screen.getByLabelText('Сумма лимита'), '100')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Лимит уже существует')
  })
})

describe('savings goals', () => {
  it('creates, updates and deletes goals', async () => {
    let items: SavingsGoal[] = []
    const request = vi.fn(async (path: string, init?: RequestInit) => {
      if (path.startsWith('/savings-goals/?')) return [...items]
      if (path === '/savings-goals/' && init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        expect(body).toEqual({ name: 'Отпуск', amount: '1000.00', status: '0', currency: 'BYN' })
        items = [{ id: 4, user_id: 1, ...body }]; return items[0]
      }
      if (path === '/savings-goals/4' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body))
        expect(body.status).toBe('250.50')
        items = [{ ...items[0], ...body }]; return items[0]
      }
      if (path === '/savings-goals/4' && init?.method === 'DELETE') { items = []; return undefined }
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount('/savings', request)
    await screen.findByText('Целей пока нет. Добавьте первую цель.')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить цель' }))
    await userEvent.type(screen.getByLabelText('Название цели'), 'Отпуск')
    await userEvent.type(screen.getByLabelText('Целевая сумма'), '1000,00')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await screen.findByText('Отпуск')
    await userEvent.click(screen.getByRole('button', { name: 'Изменить цель Отпуск' }))
    await userEvent.clear(screen.getByLabelText('Уже отложено'))
    await userEvent.type(screen.getByLabelText('Уже отложено'), '250,50')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await screen.findByText(/Отложено 250.50/)
    await userEvent.click(screen.getByRole('button', { name: 'Удалить цель Отпуск' }))
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Удалить цель' }))
    await screen.findByText('Целей пока нет. Добавьте первую цель.')
  })
})
