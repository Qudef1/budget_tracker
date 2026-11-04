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

type Request = <T>(path: string, init?: RequestInit) => Promise<T>

export async function getAllCategories(request: Request): Promise<Category[]> {
  const all: Category[] = []
  const limit = 100
  for (;;) {
    const page = await request<Category[]>(`/categories/?skip=${all.length}&limit=${limit}`)
    all.push(...page)
    if (page.length < limit) return all
  }
}

export function jsonBody(method: 'POST' | 'PATCH', data: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Не удалось выполнить запрос.'
}
