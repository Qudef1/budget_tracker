import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { decimalInput, errorMessage, getAllPages, jsonBody } from '../api/finance'
import type { Currency, SavingsGoal } from '../api/finance'

export function SavingsPage() {
  const { request } = useAuth()
  const [items, setItems] = useState<SavingsGoal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState<SavingsGoal | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [name, setName] = useState('')
  const [amount, setAmount] = useState('')
  const [saved, setSaved] = useState('0')
  const [currency, setCurrency] = useState<Currency>('BYN')
  const [pending, setPending] = useState(false)
  const [deleting, setDeleting] = useState<SavingsGoal | null>(null)
  const version = useRef(0)

  const load = useCallback(async () => {
    const current = ++version.current
    setLoading(true); setError('')
    try { const result = await getAllPages<SavingsGoal>(request, '/savings-goals/'); if (current === version.current) setItems(result) }
    catch (cause) { if (current === version.current) setError(errorMessage(cause)) }
    finally { if (current === version.current) setLoading(false) }
  }, [request])

  // Loading reflects the lifecycle of the external request.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void load(); return () => { version.current += 1 } }, [load])

  function openForm(item?: SavingsGoal) {
    setEditing(item ?? null); setName(item?.name ?? ''); setAmount(item?.amount ?? '')
    setSaved(item?.status ?? '0'); setCurrency(item?.currency ?? 'BYN')
    setError(''); setNotice(''); setDeleting(null); setFormOpen(true)
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    const goal = decimalInput(amount), savedAmount = decimalInput(saved, true), trimmed = name.trim()
    if (!trimmed || trimmed.length > 100) { setError('Укажите название длиной до 100 символов.'); return }
    if (!goal) { setError('Целевая сумма должна быть больше нуля и содержать не более двух знаков после запятой.'); return }
    if (savedAmount === null) { setError('Укажите неотрицательную отложенную сумму с не более чем двумя знаками после запятой.'); return }
    setPending(true); setError(''); setNotice('')
    try {
      const payload = { name: trimmed, amount: goal, status: savedAmount, currency }
      await request<SavingsGoal>(editing ? `/savings-goals/${editing.id}` : '/savings-goals/', jsonBody(editing ? 'PATCH' : 'POST', payload))
      setFormOpen(false); setNotice(editing ? 'Цель обновлена.' : 'Цель создана.'); await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setPending(false) }
  }

  async function remove() {
    if (!deleting || pending) return
    setPending(true); setError(''); setNotice('')
    try {
      await request<void>(`/savings-goals/${deleting.id}`, { method: 'DELETE' })
      setDeleting(null); setNotice('Цель удалена.'); await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setPending(false) }
  }

  return <section className="finance-page" aria-labelledby="savings-heading">
    <div className="page-heading"><div><p className="page-kicker">ВАШ БЮДЖЕТ</p><h1 id="savings-heading">Накопления</h1><p>Планируйте цели и отмечайте отложенную сумму.</p></div>
      <button className="primary-button compact" disabled={pending} onClick={() => openForm()}>Добавить цель</button></div>
    {error && <div className="form-error" role="alert">{error}</div>}
    {notice && <div className="form-success" role="status">{notice}</div>}
    {formOpen && <form className="editor-panel" onSubmit={save}><h2>{editing ? 'Изменить цель' : 'Новая цель'}</h2>
      <p className="helper-text">Отложенную сумму нужно обновлять вручную.</p>
      <div className="field-grid">
        <label>Название цели<input autoFocus required maxLength={100} value={name} disabled={pending} onChange={e => setName(e.target.value)} /></label>
        <label>Целевая сумма<input required inputMode="decimal" value={amount} disabled={pending} onChange={e => setAmount(e.target.value)} placeholder="0.00" /></label>
        <label>Уже отложено<input required inputMode="decimal" value={saved} disabled={pending} onChange={e => setSaved(e.target.value)} /></label>
        <label>Валюта<select value={currency} disabled={pending} onChange={e => setCurrency(e.target.value as Currency)}><option value="BYN">BYN</option><option value="USD">USD</option></select></label>
      </div>
      <div className="actions"><button className="primary-button compact" disabled={pending}>{pending ? 'Сохраняем…' : 'Сохранить'}</button><button className="secondary-button" type="button" disabled={pending} onClick={() => setFormOpen(false)}>Отмена</button></div>
    </form>}
    {deleting && <div className="confirm-panel" role="alertdialog" aria-labelledby="delete-goal-title"><h2 id="delete-goal-title">Удалить цель «{deleting.name}»?</h2><p>Цель и введённая отложенная сумма будут удалены.</p><div className="actions"><button className="danger-button" disabled={pending} onClick={remove}>{pending ? 'Удаляем…' : 'Удалить цель'}</button><button className="secondary-button" disabled={pending} onClick={() => setDeleting(null)}>Отмена</button></div></div>}
    <div className="data-panel">
      {loading ? <p role="status">Загружаем цели…</p> : items.length === 0 && !error ? <p>Целей пока нет. Добавьте первую цель.</p> : <ul className="data-list">{items.map(item => <li className="budget-row" key={item.id}><div className="budget-row-top"><div><strong>{item.name}</strong><span>Отложено {item.status} из {item.amount} {item.currency}</span></div><div className="row-actions"><button disabled={pending} onClick={() => openForm(item)} aria-label={`Изменить цель ${item.name}`}>Изменить</button><button disabled={pending} onClick={() => { setDeleting(item); setFormOpen(false); setError(''); setNotice('') }} aria-label={`Удалить цель ${item.name}`}>Удалить</button></div></div><div className="budget-progress"><progress max={Number(item.amount)} value={Math.min(Number(item.status), Number(item.amount))} aria-label={`Накопления на цель ${item.name}`} /></div></li>)}</ul>}
      {!loading && error && <button className="secondary-button" onClick={() => void load()}>Обновить список</button>}
    </div>
  </section>
}
