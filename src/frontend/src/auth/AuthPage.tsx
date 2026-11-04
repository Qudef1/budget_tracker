import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from './AuthContext'

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { user, signIn, register } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const isRegister = mode === 'register'
  const from: unknown = location.state?.from
  const destination = typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') ? from : '/transactions'

  if (user) return <Navigate to={destination} replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    setError('')
    if (!/^[A-Za-z0-9_.-]{3,100}$/.test(username)) {
      setError('Логин: от 3 до 100 латинских букв, цифр или символов . _ -')
      return
    }
    if (password.length < 8 || password.length > 128) {
      setError('Пароль должен содержать от 8 до 128 символов.')
      return
    }
    if (isRegister && password !== confirmation) {
      setError('Пароли не совпадают.')
      return
    }
    setPending(true)
    try {
      if (isRegister) {
        await register(username, password)
        navigate('/login', { replace: true, state: { registered: true, from: destination } })
      } else {
        await signIn(username, password)
        navigate(destination, { replace: true })
      }
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Не удалось выполнить запрос. Попробуйте ещё раз.')
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="auth-card" aria-labelledby="auth-title">
      <p className="auth-eyebrow">SALDO · ЛИЧНЫЕ ФИНАНСЫ</p>
      <h1 id="auth-title">{isRegister ? 'Создать аккаунт' : 'С возвращением'}</h1>
      <p className="auth-intro">{isRegister ? 'Зарегистрируйтесь, чтобы вести свой бюджет.' : 'Войдите, чтобы продолжить работу с бюджетом.'}</p>
      {location.state?.registered && !isRegister && <p className="form-success" role="status">Аккаунт создан. Теперь войдите.</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <form onSubmit={submit} className="auth-form">
        <label htmlFor="username">Логин</label>
        <input id="username" value={username} onChange={(event) => setUsername(event.target.value)}
          autoComplete="username" required minLength={3} maxLength={100} disabled={pending} />
        <label htmlFor="password">Пароль</label>
        <input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)}
          autoComplete={isRegister ? 'new-password' : 'current-password'} required minLength={8} maxLength={128} disabled={pending} />
        {isRegister && <>
          <label htmlFor="confirmation">Повторите пароль</label>
          <input id="confirmation" type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)}
            autoComplete="new-password" required minLength={8} maxLength={128} disabled={pending} />
        </>}
        <button className="primary-button" disabled={pending} type="submit">
          {pending ? 'Подождите…' : isRegister ? 'Создать аккаунт' : 'Войти'}
        </button>
      </form>
      <p className="auth-switch">{isRegister ? 'Уже есть аккаунт?' : 'Ещё нет аккаунта?'}{' '}
        <Link to={isRegister ? '/login' : '/register'} state={{ from: destination }}>
          {isRegister ? 'Войти' : 'Зарегистрироваться'}
        </Link>
      </p>
      <p className="session-note">После обновления страницы потребуется войти снова.</p>
    </section>
  )
}
