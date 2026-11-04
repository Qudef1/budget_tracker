export type TransactionType = 'income' | 'expense'
export type Currency = 'BYN' | 'USD'
export type CategoryKind = 'system' | 'custom'

export interface Category {
  id: number
  name: string
  transaction_type: TransactionType
  category_type: CategoryKind
  month_limit: number
}

export interface Transaction {
  id: number
  transaction_type: TransactionType
  amount: string
  currency: Currency
  category_id: number | null
  operation_date: string
  comment: string | null
}

export interface TransactionInput {
  transaction_type: TransactionType
  amount: string
  currency: Currency
  category_id: number | null
  operation_date: string
  comment: string | null
}

export interface BudgetLimit {
  id: number
  user_id: number
  category_id: number
  amount: string
  currency: Currency
}

export interface LimitExecution {
  limit_id: number
  year: number
  month: number
  month_limit: string
  expense_amount: string
  usage_percent: string
  period_status: 'not_reached' | 'warning' | 'exceeded'
  warning: boolean
  exceeded: boolean
}

export interface SavingsGoal {
  id: number
  user_id: number
  name: string
  amount: string
  currency: Currency
  status: string
}

export interface MonthlySummary {
  year: number
  month: number
  currency: Currency
  total_income: string
  total_expenses: string
  balance: string
}

export interface MonthComparison {
  first: MonthlySummary
  second: MonthlySummary
  income_change: string
  expenses_change: string
  balance_change: string
  income_change_percent: string | null
  expenses_change_percent: string | null
}

export interface ExpensesByCategory {
  year: number
  month: number
  currency: Currency
  total_expenses: string
  categories: { category_id: number | null; category_name: string | null; amount: string; percentage: string }[]
}

type Request = <T>(path: string, init?: RequestInit) => Promise<T>

export async function getAllPages<T>(request: Request, path: string): Promise<T[]> {
  const all: T[] = []
  const limit = 100
  for (;;) {
    const page = await request<T[]>(`${path}?skip=${all.length}&limit=${limit}`)
    all.push(...page)
    if (page.length < limit) return all
  }
}

export async function getAllCategories(request: Request): Promise<Category[]> {
  return getAllPages<Category>(request, '/categories/')
}

export function decimalInput(value: string, allowZero = false): string | null {
  const normalized = value.trim().replace(',', '.')
  if (!/^\d{1,8}(?:\.\d{1,2})?$/.test(normalized)) return null
  return allowZero || Number(normalized) > 0 ? normalized : null
}

/** Sum normalized two-decimal money strings without floating-point arithmetic. */
export function addMoney(left: string, right: string): string | null {
  function cents(value: string): bigint | null {
    const normalized = decimalInput(value, true)
    if (normalized === null) return null
    const [whole, fraction = ''] = normalized.split('.')
    return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'))
  }
  const a = cents(left), b = cents(right)
  if (a === null || b === null) return null
  const total = a + b
  if (total > 9_999_999_999n) return null
  return `${total / 100n}.${String(total % 100n).padStart(2, '0')}`
}

export function jsonBody(method: 'POST' | 'PATCH', data: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Не удалось выполнить запрос.'
}
