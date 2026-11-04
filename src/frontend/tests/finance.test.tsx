import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../src/App'
import { AuthContext } from '../src/auth/AuthContext'
import type { AuthContextValue } from '../src/auth/AuthContext'
import { ApiError } from '../src/api/client'
import type { Category, Transaction } from '../src/api/finance'

function mount(path: string, request: AuthContextValue['request']) {
  const auth: AuthContextValue = { user: { id: 1, username: 'test', role: 'USER', is_blocked: false },
    signIn: async () => undefined, signOut: () => undefined, register: async () => undefined,
    getToken: () => 'token', request }
  return render(<MemoryRouter initialEntries={[path]}><AuthContext.Provider value={auth}><App /></AuthContext.Provider></MemoryRouter>)
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('categories', () => {
  it('creates, updates and deletes a category with an explicit warning', async () => {
    let items: Category[] = []
    const request = vi.fn(async (path: string, init?: RequestInit) => {
      if (path.startsWith('/categories/?')) return [...items]
      if (path === '/categories/' && init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        expect(body.category_type).toBe('custom')
        items = [{ id: 1, ...body, month_limit: 1000 }]
        return items[0]
      }
      if (path === '/categories/1' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body))
        items = [{ ...items[0], ...body }]
        return items[0]
      }
      if (path === '/categories/1' && init?.method === 'DELETE') { items = []; return undefined }
      throw new Error(`Unexpected ${path}`)
    }) as AuthContextValue['request']
    mount('/categories', request)
    await screen.findByText('Категорий пока нет. Создайте первую категорию.')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить категорию' }))
    await userEvent.type(screen.getByLabelText('Название'), 'Продукты')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await screen.findByText('Продукты')
    await userEvent.click(screen.getByRole('button', { name: 'Изменить категорию Продукты' }))
    await userEvent.clear(screen.getByLabelText('Название'))
    await userEvent.type(screen.getByLabelText('Название'), 'Еда')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await screen.findByText('Еда')
    await userEvent.click(screen.getByRole('button', { name: 'Удалить категорию Еда' }))
    const dialog = screen.getByRole('alertdialog')
    expect(dialog.textContent).toContain('Операции сохранятся без категории')
    expect(dialog.textContent).toContain('лимиты будут архивированы')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Удалить категорию' }))
    await screen.findByText('Категорий пока нет. Создайте первую категорию.')
  })

  it('shows a server error on category update', async () => {
    const category = { id: 1, name: 'Еда', transaction_type: 'expense', category_type: 'custom', month_limit: 1000 }
    const request = vi.fn(async (path: string, init?: RequestInit) => {
      if (path.startsWith('/categories/?')) return [category]
      if (init?.method === 'PATCH') throw new ApiError(409, 'Нельзя изменить тип категории с привязанными операциями')
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount('/categories', request)
    await screen.findByText('Еда')
    await userEvent.click(screen.getByRole('button', { name: 'Изменить категорию Еда' }))
    await userEvent.selectOptions(screen.getByLabelText('Тип'), 'income')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Нельзя изменить тип категории')
  })
})

describe('transactions', () => {
  it('creates, edits and deletes an operation with nullable category and decimal string', async () => {
    const category: Category = { id: 8, name: 'Продукты', transaction_type: 'expense', category_type: 'custom', month_limit: 1000 }
    let items: Transaction[] = []
    const request = vi.fn(async (path: string, init?: RequestInit) => {
      if (path.startsWith('/categories/?')) return [category]
      if (path.startsWith('/transactions/?')) return [...items]
      if (path === '/transactions/' && init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        expect(body.amount).toBe('42.50')
        expect(body.category_id).toBe(8)
        items = [{ id: 5, ...body }]
        return items[0]
      }
      if (path === '/transactions/5' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body))
        expect(body.category_id).toBeNull()
        items = [{ id: 5, ...body }]
        return items[0]
      }
      if (path === '/transactions/5' && init?.method === 'DELETE') { items = []; return undefined }
      throw new Error(`Unexpected ${path}`)
    }) as AuthContextValue['request']
    mount('/transactions', request)
    await screen.findByText('Операций пока нет. Добавьте первую операцию.')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить операцию' }))
    await userEvent.type(screen.getByLabelText('Сумма'), '42,50')
    await userEvent.selectOptions(screen.getByLabelText('Категория'), '8')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    expect(await screen.findByText('Продукты')).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'Изменить операцию 5' }))
    await userEvent.selectOptions(screen.getByLabelText('Тип'), 'income')
    expect((screen.getByLabelText('Категория') as HTMLSelectElement).value).toBe('')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await screen.findByText('Без категории')
    await userEvent.click(screen.getByRole('button', { name: 'Удалить операцию 5' }))
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Удалить операцию' }))
    await screen.findByText('Операций пока нет. Добавьте первую операцию.')
  })

  it('loads all categories when the API returns multiple pages', async () => {
    const firstPage = Array.from({ length: 100 }, (_, i) => ({ id: i + 1, name: `Категория ${i + 1}`, transaction_type: 'expense', category_type: 'custom', month_limit: 1000 }))
    const request = vi.fn(async (path: string) => {
      if (path.includes('skip=100')) return [{ ...firstPage[0], id: 101, name: 'Последняя категория' }]
      if (path.startsWith('/categories/?')) return firstPage
      if (path.startsWith('/transactions/?')) return []
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount('/transactions', request)
    await screen.findByText('Операций пока нет. Добавьте первую операцию.')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить операцию' }))
    await waitFor(() => expect(within(screen.getByLabelText('Категория')).getByText('Последняя категория')).toBeTruthy())
  })

  it('requests the next page of transactions', async () => {
    const firstPage = Array.from({ length: 100 }, (_, i) => ({ id: i + 1, transaction_type: 'expense',
      amount: '1.00', currency: 'BYN', category_id: null, operation_date: '2026-11-01', comment: null }))
    const request = vi.fn(async (path: string) => {
      if (path.startsWith('/categories/?')) return []
      if (path.includes('/transactions/?skip=100')) return [{ ...firstPage[0], id: 101, comment: 'Вторая страница' }]
      if (path.startsWith('/transactions/?')) return firstPage
      throw new Error('Unexpected request')
    }) as AuthContextValue['request']
    mount('/transactions', request)
    await screen.findAllByText('Без категории')
    await userEvent.click(screen.getByRole('button', { name: 'Далее' }))
    expect((await screen.findByText(/Вторая страница/)).textContent).toContain('Вторая страница')
    expect(screen.getByText('Страница 2')).toBeTruthy()
  })
})
