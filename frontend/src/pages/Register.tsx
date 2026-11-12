import { useEffect, useState } from 'react'
import { getErrorMessage } from '../services/api'
import { commercialAuthApi } from '../services/commercialApi'
import { AuthShell } from '../components/auth/AuthShell'
import { Button } from '../components/Button'

interface RegisterPageProps {
  onAuthenticated: () => void
  onNavigate: (path: string) => void
}

export function Register({ onAuthenticated, onNavigate }: RegisterPageProps) {
  const [tenantName, setTenantName] = useState('')
  const [username, setUsername] = useState('')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
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
      const result = await commercialAuthApi.sendSmsCode(phone.trim(), 'register')
      setCooldown(result.cooldown || 60)
      setNotice(
        result.debug_code
          ? `验证码已发送（开发环境验证码：${result.debug_code}）`
          : '验证码已发送，请查收短信',
      )
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSendingCode(false)
    }
  }

  const submit = async () => {
    if (!tenantName.trim() || !username.trim() || !phone.trim() || !code.trim() || !password) {
      setError('请完整填写企业名称、管理员账号、手机号和验证码')
      return
    }
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }
    if (password.length < 8) {
      setError('密码长度至少 8 位')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const result = await commercialAuthApi.register({
        tenant_name: tenantName.trim(),
        username: username.trim(),
        password,
        phone: phone.trim(),
        code: code.trim(),
      })
      commercialAuthApi.persistLogin(result.tokens)
      await onAuthenticated()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="注册企业账号"
      subtitle="创建企业空间并成为管理员，注册后自动开通 14 天试用"
      footer={
        <>
          已有企业账号？{' '}
          <button
            type="button"
            className="font-medium text-sky-600 hover:text-sky-700"
            onClick={() => onNavigate('/login')}
          >
            返回登录
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <label className="block text-sm font-medium text-slate-700">
          企业名称
          <input
            value={tenantName}
            onChange={(event) => setTenantName(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            placeholder="例如：沙笛旅行社"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          管理员用户名
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            placeholder="3-32 位字母、数字或下划线"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          手机号
          <div className="mt-1 flex gap-2">
            <input
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              inputMode="tel"
              autoComplete="tel"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              placeholder="用于登录和找回密码"
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
        <label className="block text-sm font-medium text-slate-700">
          短信验证码
          <input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            inputMode="numeric"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            placeholder="6 位验证码"
          />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium text-slate-700">
            登录密码
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              placeholder="至少 8 位"
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            确认密码
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              autoComplete="new-password"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              placeholder="再次输入密码"
            />
          </label>
        </div>

        {error ? (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        ) : null}
        {notice ? <p className="text-sm text-emerald-600">{notice}</p> : null}

        <Button className="w-full" loading={submitting} onClick={() => void submit()}>
          创建企业并登录
        </Button>
      </div>
    </AuthShell>
  )
}
