import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { decimalInput, errorMessage, getAllCategories, getAllPages, jsonBody } from '../api/finance'
import type { BudgetLimit, Category, Currency, LimitExecution } from '../api/finance'

function minskMonth() {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Minsk', year: 'numeric', month: '2-digit' }).formatToParts(new Date())
  return `${parts.find(part => part.type === 'year')?.value}-${parts.find(part => part.type === 'month')?.value}`
}

function statusText(value: LimitExecution['period_status']) {
  return value === 'exceeded' ? 'Лимит превышен' : value === 'warning' ? 'Больше 80% лимита' : 'Лимит не достигнут'
}

export function BudgetsPage() {
  const { request } = useAuth()
  const [items, setItems] = useState<BudgetLimit[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [execution, setExecution] = useState<Record<number, LimitExecution | string>>({})
  const [month, setMonth] = useState(minskMonth)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState<BudgetLimit | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [category, setCategory] = useState('')
  const [currency, setCurrency] = useState<Currency>('BYN')
  const [amount, setAmount] = useState('')
  const [pending, setPending] = useState(false)
  const [deleting, setDeleting] = useState<BudgetLimit | null>(null)
  const [historyId, setHistoryId] = useState('')
  const [history, setHistory] = useState<LimitExecution[] | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [historyTitle, setHistoryTitle] = useState('')
  const version = useRef(0)
  const historyVersion = useRef(0)

  const load = useCallback(async () => {
    const current = ++version.current
    setLoading(true); setError('')
    try {
      const [limits, categoryList] = await Promise.all([
        getAllPages<BudgetLimit>(request, '/budgets/limits'), getAllCategories(request),
      ])
      const [year, monthNumber] = month.split('-').map(Number)
      const results = await Promise.allSettled(limits.map(item => request<LimitExecution>(`/budgets/limits/${item.id}/execution?year=${year}&month=${monthNumber}`)))
      if (current !== version.current) return
      setItems(limits); setCategories(categoryList)
      setExecution(Object.fromEntries(results.map((result, index) => [limits[index].id,
        result.status === 'fulfilled' ? result.value : errorMessage(result.reason)])))
    } catch (cause) { if (current === version.current) setError(errorMessage(cause)) }
    finally { if (current === version.current) setLoading(false) }
  }, [request, month])

  // Synchronize the selected period with the API.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void load(); return () => { version.current += 1 } }, [load])
  useEffect(() => () => { historyVersion.current += 1 }, [])

  function openForm(item?: BudgetLimit) {
    setEditing(item ?? null); setCategory(item ? String(item.category_id) : '')
    setCurrency(item?.currency ?? 'BYN'); setAmount(item?.amount ?? '')
    setFormOpen(true); setDeleting(null); setError(''); setNotice('')
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    const value = decimalInput(amount)
    if (!value) { setError('Введите сумму больше нуля: до 8 цифр до запятой и до 2 после.'); return }
    if (!editing && !category) { setError('Выберите категорию расходов.'); return }
    setPending(true); setError(''); setNotice('')
    try {
      const data = editing ? { amount: value } : { amount: value, category_id: Number(category), currency }
      await request<BudgetLimit>(editing ? `/budgets/limits/${editing.id}` : '/budgets/limits', jsonBody(editing ? 'PATCH' : 'POST', data))
      setFormOpen(false); setNotice(editing ? 'Лимит изменён.' : 'Лимит создан.')
      historyVersion.current += 1; setHistoryLoading(false); setHistory(null); await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setPending(false) }
  }

  async function remove() {
    if (!deleting || pending) return
    setPending(true); setError(''); setNotice('')
    try {
      const id = deleting.id
      await request<void>(`/budgets/limits/${id}`, { method: 'DELETE' })
      historyVersion.current += 1; setHistoryLoading(false)
      setDeleting(null); setHistoryId(String(id)); setHistory(null)
      setNotice(`Лимит №${id} архивирован. Его историю можно открыть по ID ниже.`)
      await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setPending(false) }
  }

  async function openHistory(id: string) {
    if (!/^[1-9]\d{0,9}$/.test(id) || Number(id) > 2147483647) { historyVersion.current += 1; setHistoryLoading(false); setHistory(null); setHistoryError('Укажите корректный ID лимита.'); return }
    const current = ++historyVersion.current
    setHistoryId(id); setHistoryLoading(true); setHistoryError(''); setHistory(null); setHistoryTitle(id)
    try {
      const result = await request<LimitExecution[]>(`/budgets/limits/${id}/history`)
      if (current === historyVersion.current) setHistory(result)
    } catch (cause) { if (current === historyVersion.current) setHistoryError(errorMessage(cause)) }
    finally { if (current === historyVersion.current) setHistoryLoading(false) }
  }

  return <section className="finance-page" aria-labelledby="budgets-heading">
    <div className="page-heading"><div><p className="page-kicker">ВАШ БЮДЖЕТ</p><h1 id="budgets-heading">Бюджеты</h1><p>Месячные лимиты расходов по категориям и валютам.</p></div>
      <button className="primary-button compact" disabled={pending} onClick={() => openForm()}>Добавить лимит</button></div>
    {error && <div className="form-error" role="alert">{error}</div>}
    {notice && <div className="form-success" role="status">{notice}</div>}
    {formOpen && <form className="editor-panel" onSubmit={save}>
      <h2>{editing ? 'Изменить лимит' : 'Новый лимит'}</h2>
      <p className="helper-text">{editing ? 'Новая сумма действует с текущего месяца; предыдущие периоды сохраняются.' : 'Лимит повторяется каждый месяц.'}</p>
      <div className="field-grid">
        <label>Категория расходов<select required value={category} disabled={pending || loading || !!editing} onChange={e => setCategory(e.target.value)}><option value="">Выберите категорию</option>{categories.filter(item => item.transaction_type === 'expense').map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Валюта<select value={currency} disabled={pending || !!editing} onChange={e => setCurrency(e.target.value as Currency)}><option value="BYN">BYN</option><option value="USD">USD</option></select></label>
        <label>Сумма лимита<input required inputMode="decimal" placeholder="0.00" value={amount} disabled={pending} onChange={e => setAmount(e.target.value)} /></label>
      </div>
      <div className="actions"><button className="primary-button compact" disabled={pending || loading}>{pending ? 'Сохраняем…' : 'Сохранить'}</button><button type="button" className="secondary-button" disabled={pending} onClick={() => setFormOpen(false)}>Отмена</button></div>
    </form>}
    {deleting && <div className="confirm-panel" role="alertdialog" aria-labelledby="delete-limit-title"><h2 id="delete-limit-title">Удалить лимит №{deleting.id}?</h2><p>Лимит будет архивирован, а его история сохранится. Сохраните ID для поиска истории после перезагрузки.</p><div className="actions"><button className="danger-button" disabled={pending} onClick={remove}>{pending ? 'Удаляем…' : 'Удалить лимит'}</button><button className="secondary-button" disabled={pending} onClick={() => setDeleting(null)}>Отмена</button></div></div>}
    <div className="data-panel">
      <div className="panel-title"><h2>Действующие лимиты</h2><label className="period-input">Месяц <input type="month" min="0001-01" max={minskMonth()} value={month} onChange={e => { if (e.target.value && e.target.value <= minskMonth()) setMonth(e.target.value) }} /></label></div>
      {loading ? <p role="status">Загружаем лимиты…</p> : items.length === 0 && !error ? <p>Лимитов пока нет.</p> : <ul className="data-list">{items.map(item => {
        const progress = execution[item.id]
        return <li className="budget-row" key={item.id}><div className="budget-row-top"><div><strong>{categories.find(categoryItem => categoryItem.id === item.category_id)?.name ?? `Категория №${item.category_id}`}</strong><span>Лимит №{item.id} · {item.amount} {item.currency}</span></div><div className="row-actions"><button disabled={pending} onClick={() => openForm(item)} aria-label={`Изменить лимит ${item.id}`}>Изменить</button><button disabled={pending} onClick={() => { setFormOpen(false); setDeleting(item); setError(''); setNotice('') }} aria-label={`Удалить лимит ${item.id}`}>Удалить</button><button onClick={() => void openHistory(String(item.id))} aria-label={`История лимита ${item.id}`}>История</button></div></div>
          {typeof progress === 'string' ? <p className="helper-text">{progress}</p> : progress && <div className="budget-progress"><div><span>{progress.expense_amount} из {progress.month_limit} {item.currency}</span><strong>{progress.usage_percent}% · {statusText(progress.period_status)}</strong></div><progress max="100" value={Math.min(100, Number(progress.usage_percent))} aria-label={`Исполнение лимита ${item.id}`} /></div>}</li>
      })}</ul>}
      {!loading && error && <button className="secondary-button" onClick={() => void load()}>Обновить список</button>}
    </div>
    <div className="data-panel history-panel"><h2>История лимита</h2><p className="helper-text">Чтобы открыть историю архивированного лимита, укажите его ID. Для архивных лимитов сервер не возвращает валюту в истории.</p><form className="history-search" onSubmit={e => { e.preventDefault(); void openHistory(historyId) }}><label htmlFor="history-id">ID лимита</label><input id="history-id" inputMode="numeric" value={historyId} onChange={e => setHistoryId(e.target.value)} /><button className="secondary-button" disabled={historyLoading}>Показать историю</button></form>
      {historyLoading && <p role="status">Загружаем историю…</p>}{historyError && <p className="form-error" role="alert">{historyError}</p>}
      {history && <><h3>Лимит №{historyTitle}</h3>{history.length === 0 ? <p>История пуста.</p> : <ul className="history-list">{history.map(item => <li key={`${item.year}-${item.month}`}><strong>{String(item.month).padStart(2, '0')}.{item.year}</strong><span>Расход {item.expense_amount} из {item.month_limit} · {item.usage_percent}% · {statusText(item.period_status)}</span></li>)}</ul>}</>}
    </div>
  </section>
}
