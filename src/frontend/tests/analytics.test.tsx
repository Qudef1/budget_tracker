import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../src/App'
import { AuthContext } from '../src/auth/AuthContext'
import type { AuthContextValue } from '../src/auth/AuthContext'
import { ApiError } from '../src/api/client'
import { addMoney } from '../src/api/finance'

function mount(path: string, request: AuthContextValue['request']) {
  const auth: AuthContextValue = { user: { id: 1, username: 'test', role: 'USER', is_blocked: false },
    signIn: async () => undefined, signOut: () => undefined, register: async () => undefined,
    getToken: () => 'token', request }
  render(<MemoryRouter initialEntries={[path]}><AuthContext.Provider value={auth}><App /></AuthContext.Provider></MemoryRouter>)
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('financial analytics', () => {
  it('displays server totals, category percentages and undefined change; changes currency', async () => {
    const request = vi.fn(async (path: string) => {
      const usd = path.includes('currency=USD')
      const currency = usd ? 'USD' : 'BYN'
      const summary = { year: 2026, month: 11, currency, total_income: usd ? '5.00' : '100.00', total_expenses: usd ? '0.00' : '40.00', balance: usd ? '5.00' : '60.00' }
      if (path.startsWith('/analytics/monthly?')) return summary
      if (path.startsWith('/analytics/categories?')) return { year: 2026, month: 11, currency, total_expenses: usd ? '0.00' : '40.00', categories: usd ? [] : [
        { category_id: 1, category_name: 'Еда', amount: '30.00', percentage: '75.00' },
        { category_id: null, category_name: null, amount: '10.00', percentage: '25.00' },
      ] }
      if (path.startsWith('/analytics/compare?')) return { first: { ...summary, total_income: '0.00' }, second: summary,
        income_change: '100.00', expenses_change: '-10.00', balance_change: '110.00', income_change_percent: null, expenses_change_percent: '-20.00' }
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount('/analytics', request)
    expect((await screen.findByText('75.00%', { exact: false })).textContent).toContain('30.00 BYN')
    expect(screen.getByText('Без категории')).toBeTruthy()
    expect((await screen.findByText('процент не определён', { exact: false })).textContent).toContain('100.00')
    await userEvent.selectOptions(screen.getByLabelText('Валюта'), 'USD')
    expect(await screen.findByText('За этот месяц расходов нет.')).toBeTruthy()
    expect(screen.getAllByText('5.00 USD').length).toBeGreaterThan(0)
    await waitFor(() => expect(vi.mocked(request).mock.calls.some(([path]) => path.includes('/analytics/compare?') && path.includes('currency=USD'))).toBe(true))
  })

  it('shows API errors and allows retry', async () => {
    let fail = true
    const summary = { year: 2026, month: 11, currency: 'BYN', total_income: '0.00', total_expenses: '0.00', balance: '0.00' }
    const request = vi.fn(async (path: string) => {
      if (path.startsWith('/analytics/monthly')) { if (fail) throw new ApiError(500, 'Ошибка сервера'); return summary }
      if (path.startsWith('/analytics/categories')) return { year: 2026, month: 11, currency: 'BYN', total_expenses: '0.00', categories: [] }
      if (path.startsWith('/analytics/compare')) return { first: summary, second: summary, income_change: '0.00', expenses_change: '0.00', balance_change: '0.00', income_change_percent: null, expenses_change_percent: null }
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount('/analytics', request)
    expect((await screen.findByRole('alert')).textContent).toContain('Ошибка сервера')
    fail = false
    await userEvent.click(screen.getByRole('button', { name: 'Повторить' }))
    expect(await screen.findByText('За этот месяц расходов нет.')).toBeTruthy()
  })
})

describe('adding savings', () => {
  it('adds exact decimal amounts and rejects overflow', () => {
    expect(addMoney('0.10', '0.20')).toBe('0.30')
    expect(addMoney('12.3', '0.01')).toBe('12.31')
    expect(addMoney('99999999.99', '0.01')).toBeNull()
  })

  it('fetches the latest amount before adding and sends the exact total', async () => {
    let status = '0.10'
    const request = vi.fn(async (path: string, init?: RequestInit) => {
      const goal = { id: 4, user_id: 1, name: 'Отпуск', amount: '1000.00', status, currency: 'BYN' }
      if (path.startsWith('/savings-goals/?')) return [goal]
      if (path === '/savings-goals/4' && !init) { status = '0.20'; return { ...goal, status } }
      if (path === '/savings-goals/4' && init?.method === 'PATCH') {
        expect(JSON.parse(String(init.body))).toEqual({ status: '0.30' })
        status = '0.30'; return { ...goal, status }
      }
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount('/savings', request)
    await screen.findByText('Отпуск')
    await userEvent.click(screen.getByRole('button', { name: 'Пополнить цель Отпуск' }))
    await userEvent.type(screen.getByLabelText('Сумма пополнения'), '0,10')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить сумму' }))
    expect(await screen.findByText(/Отложено 0.30/)).toBeTruthy()
  })
})
