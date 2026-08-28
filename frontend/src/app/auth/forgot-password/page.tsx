"use client"

import Link from "next/link"
import { useState } from "react"
import { useAuth } from "@/components/auth-provider"

export default function ForgotPasswordPage() {
  const { resetPassword } = useAuth()
  const [email, setEmail] = useState("")
  const [error, setError] = useState("")
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError("")
    const { error: message } = await resetPassword(email)
    setLoading(false)
    if (message) setError(message)
    else setSent(true)
  }

  return <AuthCard title="重置密码">
    {sent ? <p className="text-sm leading-6 text-ink-secondary">如果该邮箱已注册，重置链接已发送。请在邮件中设置新密码。</p> : <form onSubmit={submit} className="space-y-4">
      {error && <div className="rounded-lg bg-warning-soft p-3 text-sm text-warning">{error}</div>}
      <div><label className="mb-1.5 block text-sm font-medium text-ink-secondary">登录邮箱</label><input type="email" value={email} onChange={event => setEmail(event.target.value)} required autoComplete="email" className="ui-input w-full px-4 py-2.5 text-sm" placeholder="your@email.com" /></div>
      <button type="submit" disabled={loading} className="ui-button-primary w-full">{loading ? "发送中…" : "发送重置链接"}</button>
    </form>}
    <p className="mt-6 text-center text-sm text-ink-muted"><Link href="/auth/login" className="ui-link">返回登录</Link></p>
  </AuthCard>
}

function AuthCard({ title, children }: { title: string, children: React.ReactNode }) {
  return <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4"><div className="w-full max-w-md"><div className="mb-8 text-center"><h1 className="type-h1 mb-2 text-primary-dark">InsightPro</h1><p className="type-body text-ink-muted">AI 驱动的技术解决方案洞察平台</p></div><div className="ui-card p-8"><h2 className="type-h2 mb-6 text-ink">{title}</h2>{children}</div></div></div>
}
