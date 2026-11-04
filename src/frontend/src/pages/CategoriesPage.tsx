import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { errorMessage, getAllCategories, jsonBody } from '../api/finance'
import type { Category, TransactionType } from '../api/finance'

export function CategoriesPage() {
  const { request } = useAuth()
  const [items, setItems] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Category | null>(null)
  const [name, setName] = useState('')
  const [type, setType] = useState<TransactionType>('expense')
  const [pending, setPending] = useState(false)
  const [deleting, setDeleting] = useState<Category | null>(null)
  const loadVersion = useRef(0)

  const load = useCallback(async () => {
    const version = ++loadVersion.current
    setLoading(true)
    setError('')
    try { const result = await getAllCategories(request); if (version === loadVersion.current) setItems(result) }
    catch (cause) { if (version === loadVersion.current) setError(errorMessage(cause)) }
    finally { if (version === loadVersion.current) setLoading(false) }
  }, [request])

  // Loading state tracks the lifecycle of this external request.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void load(); return () => { loadVersion.current += 1 } }, [load])

  function openForm(item?: Category) {
    setError(''); setNotice(''); setDeleting(null)
    setEditing(item ?? null); setName(item?.name ?? ''); setType(item?.transaction_type ?? 'expense')
    setFormOpen(true)
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    const trimmed = name.trim()
    if (!trimmed || trimmed.length > 100) { setError('Укажите название длиной до 100 символов.'); return }
    setPending(true); setError(''); setNotice('')
    try {
      const payload = editing
        ? { name: trimmed, transaction_type: type }
        : { name: trimmed, transaction_type: type, category_type: 'custom' }
      await request<Category>(editing ? `/categories/${editing.id}` : '/categories/', jsonBody(editing ? 'PATCH' : 'POST', payload))
      setFormOpen(false); setNotice(editing ? 'Категория обновлена.' : 'Категория создана.')
      await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setPending(false) }
  }

  async function remove() {
    if (!deleting || pending) return
    setPending(true); setError(''); setNotice('')
    try {
      await request<void>(`/categories/${deleting.id}`, { method: 'DELETE' })
      setDeleting(null); setNotice('Категория удалена.'); await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setPending(false) }
  }

  return <section className="finance-page" aria-labelledby="categories-heading">
    <div className="page-heading"><div><p className="page-kicker">ВАШ БЮДЖЕТ</p><h1 id="categories-heading">Категории</h1><p>Разделяйте доходы и расходы по категориям.</p></div>
      <button className="primary-button compact" disabled={pending} onClick={() => openForm()}>Добавить категорию</button></div>
    {error && <div className="form-error" role="alert">{error}</div>}
    {notice && <div className="form-success" role="status">{notice}</div>}
    {formOpen && <form className="editor-panel" onSubmit={save}>
      <h2>{editing ? 'Изменить категорию' : 'Новая категория'}</h2>
      <div className="field-grid"><label>Название<input autoFocus maxLength={100} required value={name} onChange={event => setName(event.target.value)} disabled={pending} /></label>
      <label>Тип<select value={type} onChange={event => setType(event.target.value as TransactionType)} disabled={pending}><option value="expense">Расход</option><option value="income">Доход</option></select></label></div>
      <div className="actions"><button className="primary-button compact" disabled={pending}>{pending ? 'Сохраняем…' : 'Сохранить'}</button><button type="button" className="secondary-button" disabled={pending} onClick={() => setFormOpen(false)}>Отмена</button></div>
    </form>}
    {deleting && <div className="confirm-panel" role="alertdialog" aria-labelledby="delete-category-title" aria-describedby="delete-category-description">
      <h2 id="delete-category-title">Удалить «{deleting.name}»?</h2>
      <p id="delete-category-description">Операции сохранятся без категории. Связанные лимиты будут архивированы, их история сохранится.</p>
      <div className="actions"><button className="danger-button" disabled={pending} onClick={remove}>{pending ? 'Удаляем…' : 'Удалить категорию'}</button><button className="secondary-button" disabled={pending} onClick={() => setDeleting(null)}>Отмена</button></div>
    </div>}
    <div className="data-panel">
      {loading ? <p role="status">Загружаем категории…</p> : items.length === 0 && !error ? <p>Категорий пока нет. Создайте первую категорию.</p> :
        <ul className="data-list">{items.map(item => <li key={item.id} className="data-row"><div><strong>{item.name}</strong><span>{item.transaction_type === 'expense' ? 'Расход' : 'Доход'}</span></div><div className="row-actions"><button disabled={pending} onClick={() => openForm(item)} aria-label={`Изменить категорию ${item.name}`}>Изменить</button><button disabled={pending} onClick={() => { setFormOpen(false); setDeleting(item); setError(''); setNotice('') }} aria-label={`Удалить категорию ${item.name}`}>Удалить</button></div></li>)}</ul>}
      {!loading && error && <button className="secondary-button" onClick={() => void load()}>Обновить список</button>}
    </div>
  </section>
}
