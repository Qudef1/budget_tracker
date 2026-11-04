import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { errorMessage } from '../api/finance'
import type { Currency, ExpensesByCategory, MonthComparison, MonthlySummary } from '../api/finance'

function currentMonth(): string {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Minsk', year: 'numeric', month: '2-digit' }).formatToParts(new Date())
  return `${parts.find(part => part.type === 'year')?.value}-${parts.find(part => part.type === 'month')?.value}`
}

function previousMonth(value: string): string {
  const [year, month] = value.split('-').map(Number)
  return month === 1 ? `${String(year - 1).padStart(4, '0')}-12` : `${year}-${String(month - 1).padStart(2, '0')}`
}

function validMonth(value: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(value)
  return !!match && Number(match[1]) >= 1 && Number(match[1]) <= 9998 && Number(match[2]) >= 1 && Number(match[2]) <= 12
}

function monthQuery(value: string) {
  const [year, month] = value.split('-')
  return `year=${Number(year)}&month=${Number(month)}`
}

function displayChange(amount: string, percent: string | null, currency: Currency) {
  const prefix = Number(amount) > 0 ? '+' : ''
  return `${prefix}${amount} ${currency} · ${percent === null ? 'процент не определён' : `${Number(percent) > 0 ? '+' : ''}${percent}%`}`
}

export function AnalyticsPage() {
  const { request } = useAuth()
  const [month, setMonth] = useState(currentMonth)
  const [first, setFirst] = useState(() => previousMonth(currentMonth()))
  const [second, setSecond] = useState(currentMonth)
  const [currency, setCurrency] = useState<Currency>('BYN')
  const [summary, setSummary] = useState<MonthlySummary | null>(null)
  const [categories, setCategories] = useState<ExpensesByCategory | null>(null)
  const [comparison, setComparison] = useState<MonthComparison | null>(null)
  const [monthLoading, setMonthLoading] = useState(true)
  const [compareLoading, setCompareLoading] = useState(true)
  const [monthError, setMonthError] = useState('')
  const [compareError, setCompareError] = useState('')
  const monthVersion = useRef(0)
  const compareVersion = useRef(0)

  const loadMonth = useCallback(async () => {
    const version = ++monthVersion.current
    setMonthLoading(true); setMonthError(''); setSummary(null); setCategories(null)
    if (!validMonth(month)) { setMonthError('Выберите месяц с годом от 1 до 9998.'); setMonthLoading(false); return }
    try {
      const query = `${monthQuery(month)}&currency=${currency}`
      const [result, breakdown] = await Promise.all([
        request<MonthlySummary>(`/analytics/monthly?${query}`),
        request<ExpensesByCategory>(`/analytics/categories?${query}`),
      ])
      if (version === monthVersion.current) { setSummary(result); setCategories(breakdown) }
    } catch (error) { if (version === monthVersion.current) setMonthError(errorMessage(error)) }
    finally { if (version === monthVersion.current) setMonthLoading(false) }
  }, [month, currency, request])

  const loadComparison = useCallback(async () => {
    const version = ++compareVersion.current
    setCompareLoading(true); setCompareError(''); setComparison(null)
    if (!validMonth(first) || !validMonth(second)) { setCompareError('Выберите месяцы с годом от 1 до 9998.'); setCompareLoading(false); return }
    const [firstYear, firstMonth] = first.split('-').map(Number)
    const [secondYear, secondMonth] = second.split('-').map(Number)
    try {
      const result = await request<MonthComparison>(`/analytics/compare?first_year=${firstYear}&first_month=${firstMonth}&second_year=${secondYear}&second_month=${secondMonth}&currency=${currency}`)
      if (version === compareVersion.current) setComparison(result)
    } catch (error) { if (version === compareVersion.current) setCompareError(errorMessage(error)) }
    finally { if (version === compareVersion.current) setCompareLoading(false) }
  }, [first, second, currency, request])

  // These effects synchronize the selected periods with the backend.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void loadMonth(); return () => { monthVersion.current += 1 } }, [loadMonth])
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void loadComparison(); return () => { compareVersion.current += 1 } }, [loadComparison])

  const maxBar = summary ? Math.max(Number(summary.total_income), Number(summary.total_expenses), 1) : 1
  return <section className="finance-page" aria-labelledby="analytics-heading">
    <div className="page-heading"><div><p className="page-kicker">ВАШ БЮДЖЕТ</p><h1 id="analytics-heading">Аналитика</h1><p>Доходы, расходы и динамика за выбранный период.</p></div></div>
    <div className="data-panel"><div className="analytics-filters">
      <label>Месяц<input type="month" min="0001-01" max="9998-12" value={month} onChange={e => setMonth(e.target.value)} /></label>
      <label>Валюта<select value={currency} onChange={e => setCurrency(e.target.value as Currency)}><option value="BYN">BYN</option><option value="USD">USD</option></select></label>
    </div><p className="helper-text">Каждая валюта отображается отдельно, без конвертации.</p></div>
    {monthLoading && <div className="data-panel" role="status">Загружаем показатели…</div>}
    {monthError && <div className="form-error" role="alert">{monthError} <button className="secondary-button" onClick={() => void loadMonth()}>Повторить</button></div>}
    {summary && categories && <>
      <div className="analytics-cards">
        <article className="data-panel"><span>Доходы</span><strong>{summary.total_income} {currency}</strong></article>
        <article className="data-panel"><span>Расходы</span><strong>{summary.total_expenses} {currency}</strong></article>
        <article className="data-panel"><span>Баланс</span><strong>{summary.balance} {currency}</strong></article>
      </div>
      <div className="data-panel analytics-chart"><h2>Доходы и расходы</h2>
        <div className="chart-row"><span>Доходы</span><progress aria-label="Доходы за месяц" max={maxBar} value={Number(summary.total_income)} /><strong>{summary.total_income} {currency}</strong></div>
        <div className="chart-row"><span>Расходы</span><progress aria-label="Расходы за месяц" max={maxBar} value={Number(summary.total_expenses)} /><strong>{summary.total_expenses} {currency}</strong></div>
      </div>
      <div className="data-panel analytics-chart"><h2>Расходы по категориям</h2><p className="helper-text">Всего: {categories.total_expenses} {currency}</p>
        {categories.categories.length === 0 ? <p>За этот месяц расходов нет.</p> : <ul className="category-chart">{categories.categories.map(item => <li key={item.category_id ?? 'none'}>
          <div><strong>{item.category_name ?? 'Без категории'}</strong><span>{item.amount} {currency} · {item.percentage}%</span></div>
          <progress aria-label={`Доля расходов: ${item.category_name ?? 'Без категории'}`} max="100" value={Math.min(100, Number(item.percentage))} />
        </li>)}</ul>}
      </div>
    </>}
    <div className="data-panel analytics-chart"><h2>Сравнение месяцев</h2><p className="helper-text">Изменение рассчитано относительно первого месяца.</p>
      <div className="analytics-filters"><label>Первый месяц<input type="month" min="0001-01" max="9998-12" value={first} onChange={e => setFirst(e.target.value)} /></label><label>Второй месяц<input type="month" min="0001-01" max="9998-12" value={second} onChange={e => setSecond(e.target.value)} /></label></div>
      {compareLoading && <p role="status">Загружаем сравнение…</p>}
      {compareError && <p className="form-error" role="alert">{compareError} <button className="secondary-button" onClick={() => void loadComparison()}>Повторить</button></p>}
      {comparison && <div className="table-scroll"><table className="comparison-table"><thead><tr><th>Показатель</th><th>{first}</th><th>{second}</th><th>Изменение</th></tr></thead><tbody>
        <tr><th>Доходы</th><td>{comparison.first.total_income} {currency}</td><td>{comparison.second.total_income} {currency}</td><td>{displayChange(comparison.income_change, comparison.income_change_percent, currency)}</td></tr>
        <tr><th>Расходы</th><td>{comparison.first.total_expenses} {currency}</td><td>{comparison.second.total_expenses} {currency}</td><td>{displayChange(comparison.expenses_change, comparison.expenses_change_percent, currency)}</td></tr>
        <tr><th>Баланс</th><td>{comparison.first.balance} {currency}</td><td>{comparison.second.balance} {currency}</td><td>{Number(comparison.balance_change) > 0 ? '+' : ''}{comparison.balance_change} {currency}</td></tr>
      </tbody></table></div>}
    </div>
  </section>
}
