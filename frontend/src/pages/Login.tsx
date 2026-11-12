import { useEffect, useState } from 'react'
import { authApi, getErrorMessage } from '../services/api'
import { commercialAuthApi } from '../services/commercialApi'
import { AuthShell } from '../components/auth/AuthShell'
import { Button } from '../components/Button'

type Mode = 'password' | 'sms' | 'reset'

interface LoginPageProps {
  onAuthenticated: () => void
  onNavigate: (path: string) => void
}

export function Login({ onAuthenticated, onNavigate }: LoginPageProps) {
  const [mode, setMode] = useState<Mode>('password')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [sendingCode, setSendingCode] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = window.setInterval(() => setCooldown((value) => Math.max(value - 1, 0)), 1000)
    return () => window.clearInterval(timer)
  }, [cooldown])

  const sendCode = async () => {
    if (!phone.trim()) {
      setError('请先输入手机号')
      return
    }
    setSendingCode(true)
    setError(null)
    try {
      const result = await commercialAuthApi.sendSmsCode(
        phone.trim(),
        mode === 'reset' ? 'reset' : 'login',
      )
      setCooldown(result.cooldown || 60)
      setNotice(result.debug_code ? `验证码已发送（开发环境验证码：${result.debug_code}）` : '验证码已发送')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSendingCode(false)
    }
  }

  const submitPassword = async () => {
    if (!username.trim() || !password) {
      setError('请输入用户名和密码')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await authApi.login(username.trim(), password)
      await onAuthenticated()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const submitSms = async () => {
    if (!phone.trim() || !code.trim()) {
      setError('请输入手机号和验证码')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const result = await commercialAuthApi.loginSms(phone.trim(), code.trim())
      commercialAuthApi.persistLogin(result.tokens)
      await onAuthenticated()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const submitReset = async () => {
    if (!phone.trim() || !code.trim() || !newPassword) {
      setError('请完整填写手机号、验证码和新密码')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await commercialAuthApi.resetPassword(phone.trim(), code.trim(), newPassword)
      setNotice('密码已重置，请使用新密码登录')
      setMode('password')
      setUsername(phone.trim())
      setCode('')
      setNewPassword('')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const switchMode = (next: Mode) => {
    setMode(next)
    setError(null)
    setNotice(null)
  }

  return (
    <AuthShell
      title={mode === 'reset' ? '重置登录密码' : '登录企业工作台'}
      subtitle={
        mode === 'reset'
          ? '通过注册手机号验证后设置新密码'
          : '使用管理员分配的账号登录，或通过手机验证码快捷登录'
      }
      footer={
        <>
          还没有企业账号？{' '}
          <button
            type="button"
            className="font-medium text-sky-600 hover:text-sky-700"
            onClick={() => onNavigate('/register')}
          >
            注册企业
          </button>
        </>
      }
    >
      {mode !== 'reset' ? (
        <div className="mb-5 grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1 text-sm">
          <button
            type="button"
            onClick={() => switchMode('password')}
            className={`rounded-md px-3 py-2 font-medium transition ${
              mode === 'password' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
            }`}
          >
            账号密码
          </button>
          <button
            type="button"
            onClick={() => switchMode('sms')}
            className={`rounded-md px-3 py-2 font-medium transition ${
              mode === 'sms' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
            }`}
          >
            手机验证码
          </button>
        </div>
      ) : null}

      <div className="space-y-4">
        {mode === 'password' ? (
          <>
            <label className="block text-sm font-medium text-slate-700">
              用户名
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                placeholder="请输入用户名"
              />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              密码
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                onKeyDown={(event) => {
                  if (event.key === 'Enter') void submitPassword()
                }}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                placeholder="请输入密码"
              />
            </label>
          </>
        ) : (
          <>
            <label className="block text-sm font-medium text-slate-700">
              手机号
              <input
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                inputMode="tel"
                autoComplete="tel"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                placeholder="请输入注册手机号"
              />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              验证码
              <div className="mt-1 flex gap-2">
                <input
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  inputMode="numeric"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                  placeholder="6 位验证码"
                />
                <button
                  type="button"
                  onClick={sendCode}
                  disabled={sendingCode || cooldown > 0}
                  className="shrink-0 rounded-lg border border-slate-300 px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {cooldown > 0 ? `${cooldown}s` : sendingCode ? '发送中' : '获取验证码'}
                </button>
              </div>
            </label>
            {mode === 'reset' ? (
              <label className="block text-sm font-medium text-slate-700">
                新密码
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  autoComplete="new-password"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                  placeholder="至少 8 位，建议包含字母与数字"
                />
              </label>
            ) : null}
          </>
        )}

        {error ? (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        ) : null}
        {notice ? <p className="text-sm text-emerald-600">{notice}</p> : null}

        <Button
          className="w-full"
          loading={submitting}
          onClick={() => {
            if (mode === 'password') return void submitPassword()
            if (mode === 'sms') return void submitSms()
            return void submitReset()
          }}
        >
          {mode === 'password' ? '登录' : mode === 'sms' ? '验证码登录' : '重置密码'}
        </Button>

        <div className="flex items-center justify-between text-xs text-slate-500">
          {mode === 'reset' ? (
            <button type="button" onClick={() => switchMode('password')} className="hover:text-sky-600">
              返回登录
            </button>
          ) : (
            <button type="button" onClick={() => switchMode('reset')} className="hover:text-sky-600">
              忘记密码
            </button>
          )}
          <span>登录即代表同意企业服务协议</span>
        </div>
      </div>
    </AuthShell>
  )
}
