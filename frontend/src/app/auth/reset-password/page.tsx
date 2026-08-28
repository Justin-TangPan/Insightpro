"use client"

import Link from "next/link"
import { useState } from "react"
import { useAuth } from "@/components/auth-provider"
import { createClient } from "@/utils/supabase/client"

export default function ResetPasswordPage() {
  const { user, loading: authLoading, signOut } = useAuth()
  const [password, setPassword] = useState("")
  const [confirmation, setConfirmation] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (password !== confirmation) return setError("两次输入的密码不一致")
    setLoading(true)
    setError("")
    const { error: message } = await createClient().auth.updateUser({ password })
    setLoading(false)
    if (message) return setError(message.message)
    await signOut()
    setDone(true)
  }

  return <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4"><div className="w-full max-w-md"><div className="ui-card p-8"><h1 className="type-h2 mb-6 text-ink">设置新密码</h1>{done ? <><p className="text-sm text-ink-secondary">密码已更新，请使用新密码登录。</p><Link href="/auth/login" className="ui-button-primary mt-6">去登录</Link></> : authLoading ? <p className="text-sm text-ink-muted">正在验证重置链接…</p> : !user ? <><p className="text-sm text-ink-secondary">重置链接无效或已过期。</p><Link href="/auth/forgot-password" className="ui-link mt-5 inline-block">重新发送链接</Link></> : <form onSubmit={submit} className="space-y-4">{error && <div className="rounded-lg bg-warning-soft p-3 text-sm text-warning">{error}</div>}<div><label className="mb-1.5 block text-sm font-medium text-ink-secondary">新密码</label><input type="password" value={password} onChange={event => setPassword(event.target.value)} required minLength={6} autoComplete="new-password" className="ui-input w-full px-4 py-2.5 text-sm" /></div><div><label className="mb-1.5 block text-sm font-medium text-ink-secondary">确认新密码</label><input type="password" value={confirmation} onChange={event => setConfirmation(event.target.value)} required minLength={6} autoComplete="new-password" className="ui-input w-full px-4 py-2.5 text-sm" /></div><button type="submit" disabled={loading} className="ui-button-primary w-full">{loading ? "保存中…" : "更新密码"}</button></form>}</div></div></div>
}
