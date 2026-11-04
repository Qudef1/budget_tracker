import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import type { User } from '../api/client'
import type { AdminStatistics } from '../api/admin'
import { errorMessage } from '../api/finance'

const PAGE_SIZE = 25

function currentMonth() {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Minsk', year: 'numeric', month: '2-digit' }).formatToParts(new Date())
  return `${parts.find(part => part.type === 'year')?.value}-${parts.find(part => part.type === 'month')?.value}`
}

export function AdminPage() {
  const { request, user } = useAuth()
  const [month, setMonth] = useState(currentMonth)
  const [page, setPage] = useState(0)
  const [users, setUsers] = useState<User[]>([])
  const [statistics, setStatistics] = useState<AdminStatistics | null>(null)
  const [usersLoading, setUsersLoading] = useState(true)
  const [statsLoading, setStatsLoading] = useState(true)
  const [usersError, setUsersError] = useState('')
  const [statsError, setStatsError] = useState('')
  const [notice, setNotice] = useState('')
  const [target, setTarget] = useState<User | null>(null)
  const [pending, setPending] = useState(false)
  const usersVersion = useRef(0)
  const statsVersion = useRef(0)

  const loadUsers = useCallback(async () => {
    const version = ++usersVersion.current
    setUsersLoading(true); setUsersError('')
    try {
      const result = await request<User[]>(`/admin/users?skip=${page * PAGE_SIZE}&limit=${PAGE_SIZE}`)
      if (version === usersVersion.current) setUsers(result)
    } catch (cause) { if (version === usersVersion.current) setUsersError(errorMessage(cause)) }
    finally { if (version === usersVersion.current) setUsersLoading(false) }
  }, [page, request])

  const loadStats = useCallback(async () => {
    const version = ++statsVersion.current
    setStatsLoading(true); setStatsError(''); setStatistics(null)
    const match = /^(\d{4})-(\d{2})$/.exec(month)
    if (!match || Number(match[1]) < 1 || Number(match[1]) > 9998 || Number(match[2]) < 1 || Number(match[2]) > 12) {
      setStatsError('Выберите месяц с годом от 1 до 9998.'); setStatsLoading(false); return
    }
    try {
      const result = await request<AdminStatistics>(`/admin/statistics?year=${Number(match[1])}&month=${Number(match[2])}`)
      if (version === statsVersion.current) setStatistics(result)
    } catch (cause) { if (version === statsVersion.current) setStatsError(errorMessage(cause)) }
    finally { if (version === statsVersion.current) setStatsLoading(false) }
  }, [month, request])

  // Load each independent API resource and discard stale responses.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void loadUsers(); return () => { usersVersion.current += 1 } }, [loadUsers])
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void loadStats(); return () => { statsVersion.current += 1 } }, [loadStats])

  async function changeBlock() {
    if (!target || pending || (target.id === user?.id && !target.is_blocked)) return
    const targetId = target.id
    const wasBlocked = target.is_blocked
    setPending(true); setUsersError(''); setNotice('')
    try {
      await request<User>(`/admin/users/${targetId}/${wasBlocked ? 'unblock' : 'block'}`, { method: 'PATCH' })
      setTarget(null)
      setNotice(wasBlocked ? 'Пользователь разблокирован.' : 'Пользователь заблокирован.')
      await Promise.all([loadUsers(), loadStats()])
    } catch (cause) { setUsersError(errorMessage(cause)) }
    finally { setPending(false) }
  }

  return <section className="finance-page" aria-labelledby="admin-heading">
    <div className="page-heading"><div><p className="page-kicker">УПРАВЛЕНИЕ ПРИЛОЖЕНИЕМ</p><h1 id="admin-heading">Администрирование</h1><p>Общая статистика и управление учётными записями.</p></div></div>
    <section className="data-panel" aria-labelledby="stats-heading">
      <div className="panel-title"><h2 id="stats-heading">Статистика</h2><label className="period-input">Месяц <input type="month" min="0001-01" max="9998-12" value={month} onChange={event => setMonth(event.target.value)} /></label></div>
      <p className="helper-text">Период относится к числу операций за месяц; остальные показатели — за всё время.</p>
      {statsLoading && <p role="status">Загружаем статистику…</p>}
      {statsError && <div className="form-error" role="alert">{statsError} <button className="secondary-button" onClick={() => void loadStats()}>Повторить загрузку статистики</button></div>}
      {statistics && <dl className="admin-stats">
        <div><dt>Пользователи</dt><dd>{statistics.total_users}</dd></div>
        <div><dt>Заблокированы</dt><dd>{statistics.blocked_users}</dd></div>
        <div><dt>Все операции</dt><dd>{statistics.total_transactions}</dd></div>
        <div><dt>Операции за месяц</dt><dd>{statistics.monthly_transactions}</dd></div>
        <div><dt>Цели накопления</dt><dd>{statistics.total_savings_goals}</dd></div>
        <div><dt>Пользовательские категории</dt><dd>{statistics.custom_categories}</dd></div>
      </dl>}
    </section>
    <section className="data-panel" aria-labelledby="users-heading">
      <h2 id="users-heading">Пользователи</h2>
      {notice && <div className="form-success" role="status">{notice}</div>}
      {usersError && <div className="form-error" role="alert">{usersError} <button className="secondary-button" onClick={() => void loadUsers()}>Обновить список</button></div>}
      {target && <div className="confirm-panel" role="alertdialog" aria-labelledby="block-title" aria-describedby="block-description">
        <h3 id="block-title">{target.is_blocked ? 'Разблокировать' : 'Заблокировать'} «{target.username}»?</h3>
        <p id="block-description">{target.is_blocked ? 'Пользователь снова сможет войти и выполнять запросы.' : 'Пользователь не сможет войти или продолжать работу, пока аккаунт заблокирован.'}</p>
        <div className="actions"><button className={target.is_blocked ? 'secondary-button' : 'danger-button'} disabled={pending} onClick={() => void changeBlock()}>{pending ? 'Сохраняем…' : target.is_blocked ? 'Разблокировать' : 'Заблокировать'}</button><button className="secondary-button" disabled={pending} onClick={() => setTarget(null)}>Отмена</button></div>
      </div>}
      {usersLoading ? <p role="status">Загружаем пользователей…</p> : users.length === 0 && !usersError ? <p>Пользователей на этой странице нет.</p> : <ul className="data-list">{users.map(item => <li className="data-row" key={item.id}>
        <div><strong>{item.username}{item.id === user?.id ? ' (вы)' : ''}</strong><span>ID {item.id} · {item.role === 'ADMIN' ? 'Администратор' : 'Пользователь'} · {item.is_blocked ? 'Заблокирован' : 'Активен'}</span></div>
        <div className="row-actions"><button disabled={pending || (item.id === user?.id && !item.is_blocked)} title={item.id === user?.id && !item.is_blocked ? 'Нельзя заблокировать себя' : undefined} aria-label={`${item.is_blocked ? 'Разблокировать' : 'Заблокировать'} пользователя ${item.username}`} onClick={() => { setTarget(item); setUsersError(''); setNotice('') }}>{item.is_blocked ? 'Разблокировать' : 'Заблокировать'}</button></div>
      </li>)}</ul>}
      <div className="pagination"><button className="secondary-button" disabled={usersLoading || pending || page === 0} onClick={() => { setTarget(null); setPage(page - 1) }}>Назад</button><span>Страница {page + 1}</span><button className="secondary-button" disabled={usersLoading || pending || users.length < PAGE_SIZE} onClick={() => { setTarget(null); setPage(page + 1) }}>Далее</button></div>
    </section>
  </section>
}
