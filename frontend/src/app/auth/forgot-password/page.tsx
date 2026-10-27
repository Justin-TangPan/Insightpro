"use client"

import Link from "next/link"
import { Radar } from "lucide-react"
import { useState } from "react"
import { useAuth } from "@/components/auth-provider"
import { usePreferences } from "@/lib/preferences"

export default function ForgotPasswordPage() {
  const { preferences } = usePreferences()
  const en = preferences.language === "en"
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

  return <AuthCard title={en ? "Reset password" : "重置密码"}>
    {sent ? <p className="text-sm leading-6 text-ink-secondary">{en ? "If this email is registered, a reset link has been sent. Set a new password from the email." : "如果该邮箱已注册，重置链接已发送。请在邮件中设置新密码。"}</p> : <form onSubmit={submit} className="space-y-4">
      {error && <div className="rounded-lg bg-warning-soft p-3 text-sm text-warning">{error}</div>}
      <div><label className="mb-1.5 block text-sm font-medium text-ink-secondary">{en ? "Sign-in email" : "登录邮箱"}</label><input type="email" value={email} onChange={event => setEmail(event.target.value)} required autoComplete="email" className="ui-input w-full px-4 py-2.5 text-sm" placeholder="your@email.com" /></div>
      <button type="submit" disabled={loading} className="ui-button-primary w-full">{loading ? (en ? "Sending..." : "发送中…") : (en ? "Send reset link" : "发送重置链接")}</button>
    </form>}
    <p className="mt-6 text-center text-sm text-ink-muted"><Link href="/auth/login" className="ui-link">{en ? "Back to sign in" : "返回登录"}</Link></p>
  </AuthCard>
}

function AuthCard({ title, children }: { title: string, children: React.ReactNode }) {
  const { preferences } = usePreferences()
  return <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4"><div className="w-full max-w-md"><div className="mb-8 text-center"><Radar className="mx-auto mb-4 h-16 w-16 rounded-2xl bg-blue-50 p-4 text-primary" aria-label="小雷达" /><p className="type-body text-ink-muted">{preferences.language === "en" ? "AI-powered technology solution insights" : "AI 驱动的技术解决方案洞察平台"}</p></div><div className="ui-card p-8"><h2 className="type-h2 mb-6 text-ink">{title}</h2>{children}</div></div></div>
}
