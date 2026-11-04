import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { errorMessage, getAllCategories, jsonBody } from '../api/finance'
import type { Category, Currency, Transaction, TransactionInput, TransactionType } from '../api/finance'

const PAGE_SIZE = 100

function today() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function emptyForm(): TransactionInput {
  return { transaction_type: 'expense', amount: '', currency: 'BYN', category_id: null, operation_date: today(), comment: '' }
}

export function TransactionsPage() {
  const { request } = useAuth()
  const [items, setItems] = useState<Transaction[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [form, setForm] = useState<TransactionInput>(emptyForm)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Transaction | null>(null)
  const [deleting, setDeleting] = useState<Transaction | null>(null)
  const [pending, setPending] = useState(false)
  const loadVersion = useRef(0)

  const load = useCallback(async () => {
    const version = ++loadVersion.current
    setLoading(true); setError('')
    try {
      const [transactions, categoryList] = await Promise.all([
        request<Transaction[]>(`/transactions/?skip=${page * PAGE_SIZE}&limit=${PAGE_SIZE}`), getAllCategories(request),
      ])
      if (version === loadVersion.current) { setItems(transactions); setCategories(categoryList) }
    } catch (cause) { if (version === loadVersion.current) setError(errorMessage(cause)) }
    finally { if (version === loadVersion.current) setLoading(false) }
  }, [page, request])

  // Loading state tracks the lifecycle of this external request.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void load(); return () => { loadVersion.current += 1 } }, [load])

  function openForm(item?: Transaction) {
    setError(''); setNotice(''); setDeleting(null); setEditing(item ?? null)
    setForm(item ? { transaction_type: item.transaction_type, amount: item.amount, currency: item.currency,
      category_id: item.category_id, operation_date: item.operation_date, comment: item.comment ?? '' } : emptyForm())
    setFormOpen(true)
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    const amount = form.amount.trim().replace(',', '.')
    if (!/^\d{1,8}(?:\.\d{1,2})?$/.test(amount) || Number(amount) <= 0) {
      setError('Введите сумму больше нуля: до 8 цифр до запятой и до 2 после.')
      return
    }
    if (!form.operation_date) { setError('Укажите дату операции.'); return }
    setPending(true); setError(''); setNotice('')
    try {
      const payload = { ...form, amount, comment: form.comment?.trim() || null }
      await request<Transaction>(editing ? `/transactions/${editing.id}` : '/transactions/', jsonBody(editing ? 'PATCH' : 'POST', payload))
      setFormOpen(false); setNotice(editing ? 'Операция обновлена.' : 'Операция добавлена.')
      if (!editing && page !== 0) setPage(0)
      else await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setPending(false) }
  }

  async function remove() {
    if (!deleting || pending) return
    setPending(true); setError(''); setNotice('')
    try {
      await request<void>(`/transactions/${deleting.id}`, { method: 'DELETE' })
      setDeleting(null); setNotice('Операция удалена.')
      if (items.length === 1 && page > 0) setPage(page - 1)
      else await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setPending(false) }
  }

  return <section className="finance-page" aria-labelledby="transactions-heading">
    <div className="page-heading"><div><p className="page-kicker">ВАШ БЮДЖЕТ</p><h1 id="transactions-heading">Операции</h1><p>Следите за своими доходами и расходами.</p></div>
      <button className="primary-button compact" disabled={pending} onClick={() => openForm()}>Добавить операцию</button></div>
    {error && <div className="form-error" role="alert">{error}</div>}
    {notice && <div className="form-success" role="status">{notice}</div>}
    {formOpen && <form className="editor-panel" onSubmit={save}>
      <h2>{editing ? 'Изменить операцию' : 'Новая операция'}</h2>
      <div className="field-grid">
        <label>Тип<select value={form.transaction_type} disabled={pending} onChange={event => setForm({ ...form, transaction_type: event.target.value as TransactionType, category_id: null })}><option value="expense">Расход</option><option value="income">Доход</option></select></label>
        <label>Сумма<input inputMode="decimal" required value={form.amount} disabled={pending} onChange={event => setForm({ ...form, amount: event.target.value })} placeholder="0.00" /></label>
        <label>Валюта<select value={form.currency} disabled={pending} onChange={event => setForm({ ...form, currency: event.target.value as Currency })}><option value="BYN">BYN</option><option value="USD">USD</option></select></label>
        <label>Категория<select value={form.category_id ?? ''} disabled={pending || loading} onChange={event => setForm({ ...form, category_id: event.target.value ? Number(event.target.value) : null })}><option value="">Без категории</option>{categories.filter(item => item.transaction_type === form.transaction_type).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Дата<input type="date" required value={form.operation_date} disabled={pending} onChange={event => setForm({ ...form, operation_date: event.target.value })} /></label>
        <label>Комментарий<input maxLength={500} value={form.comment ?? ''} disabled={pending} onChange={event => setForm({ ...form, comment: event.target.value })} /></label>
      </div>
      <div className="actions"><button className="primary-button compact" disabled={pending || loading}>{pending ? 'Сохраняем…' : 'Сохранить'}</button><button type="button" className="secondary-button" disabled={pending} onClick={() => setFormOpen(false)}>Отмена</button></div>
    </form>}
    {deleting && <div className="confirm-panel" role="alertdialog" aria-labelledby="delete-transaction-title"><h2 id="delete-transaction-title">Удалить операцию?</h2><p>Операция от {deleting.operation_date} на сумму {deleting.amount} {deleting.currency} будет удалена.</p><div className="actions"><button className="danger-button" disabled={pending} onClick={remove}>{pending ? 'Удаляем…' : 'Удалить операцию'}</button><button className="secondary-button" disabled={pending} onClick={() => setDeleting(null)}>Отмена</button></div></div>}
    <div className="data-panel">
      {loading ? <p role="status">Загружаем операции…</p> : items.length === 0 && !error ? <p>{page === 0 ? 'Операций пока нет. Добавьте первую операцию.' : 'На этой странице операций нет.'}</p> :
        <ul className="data-list">{items.map(item => <li key={item.id} className="data-row transaction-row"><div><strong>{categories.find(category => category.id === item.category_id)?.name ?? 'Без категории'}</strong><span>{item.operation_date}{item.comment ? ` · ${item.comment}` : ''}</span></div><div className="row-end"><strong className={item.transaction_type === 'income' ? 'income' : 'expense'}>{item.transaction_type === 'income' ? '+' : '−'}{item.amount} {item.currency}</strong><div className="row-actions"><button disabled={pending} aria-label={`Изменить операцию ${item.id}`} onClick={() => openForm(item)}>Изменить</button><button disabled={pending} aria-label={`Удалить операцию ${item.id}`} onClick={() => { setFormOpen(false); setDeleting(item); setError(''); setNotice('') }}>Удалить</button></div></div></li>)}</ul>}
      {!loading && error && <button className="secondary-button" onClick={() => void load()}>Обновить список</button>}
      <div className="pagination"><button className="secondary-button" disabled={loading || pending || page === 0} onClick={() => setPage(page - 1)}>Назад</button><span>Страница {page + 1}</span><button className="secondary-button" disabled={loading || pending || items.length < PAGE_SIZE} onClick={() => setPage(page + 1)}>Далее</button></div>
    </div>
  </section>
}
