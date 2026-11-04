import { Link, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import { AuthPage } from './auth/AuthPage'
import { useAuth } from './auth/AuthContext'
import { RequireAdmin, RequireUser } from './auth/RouteGuards'
import { CategoriesPage } from './pages/CategoriesPage'
import { TransactionsPage } from './pages/TransactionsPage'
import { BudgetsPage } from './pages/BudgetsPage'
import { SavingsPage } from './pages/SavingsPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { AdminPage } from './pages/AdminPage'
import './App.css'

const sections = [
  { path: '/transactions', label: 'Операции' },
  { path: '/categories', label: 'Категории' },
  { path: '/budgets', label: 'Бюджеты' },
  { path: '/savings', label: 'Накопления' },
  { path: '/analytics', label: 'Аналитика' },
]

function AppShell() {
  const { user, signOut } = useAuth()
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link className="brand" to="/">Saldo</Link>
        {user && <nav aria-label="Основная навигация" className="navigation">
          {sections.map(({ path, label }) => (
            <NavLink key={path} to={path} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              {label}
            </NavLink>
          ))}
          {user.role === 'ADMIN' && <NavLink to="/admin" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Администрирование</NavLink>}
        </nav>}
        {user ? <div className="account"><span className="account-name">{user.username}</span><button className="text-button" onClick={signOut}>Выйти</button></div>
          : <Link className="signin-link" to="/login">Вход</Link>}
      </header>
      <main className="page-content"><Outlet /></main>
    </div>
  )
}

function StageNotice({ title, children }: { title: string; children: string }) {
  return (
    <section className="stage-notice" aria-labelledby="page-title">
      <span className="stage-label">В разработке</span>
      <h1 id="page-title">{title}</h1>
      <p>{children}</p>
    </section>
  )
}

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<StageNotice title="Saldo">Интерфейс управления финансами находится в разработке.</StageNotice>} />
        <Route path="login" element={<AuthPage key="login" mode="login" />} />
        <Route path="register" element={<AuthPage key="register" mode="register" />} />
        <Route element={<RequireUser />}>
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="categories" element={<CategoriesPage />} />
        <Route path="budgets" element={<BudgetsPage />} />
        <Route path="savings" element={<SavingsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="forbidden" element={<StageNotice title="Доступ запрещён">Этот раздел доступен только администратору.</StageNotice>} />
        <Route element={<RequireAdmin />}>
          <Route path="admin" element={<AdminPage />} />
        </Route>
        </Route>
        <Route path="*" element={<StageNotice title="Страница не найдена">Проверьте адрес или выберите раздел в меню.</StageNotice>} />
      </Route>
    </Routes>
  )
}

export default App
