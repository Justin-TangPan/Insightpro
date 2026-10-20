"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@/components/auth-provider"
import Link from "next/link"
import Image from "next/image"
import { usePreferences } from "@/lib/preferences"

export default function LoginPage() {
  const { preferences } = usePreferences()
  const en = preferences.language === "en"
  const { user, loading: authLoading, signIn } = useAuth()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!authLoading && user) window.location.replace(returnPath())
  }, [authLoading, user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    const { error: err } = await signIn(username, password)
    setLoading(false)
    if (err) {
      setError(err)
    } else {
      window.location.href = returnPath()
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Image src="/brand/insightpro-logo.png" alt="InsightPro" width={128} height={128} className="mx-auto mb-4 rounded-2xl shadow-[var(--shadow-card)]" priority />
          <p className="type-body text-ink-muted">{en ? "Internal preview" : "内测用户登录"}</p>
        </div>

        <div className="ui-card p-8">
          <h2 className="type-h2 mb-6 text-ink">{en ? "Sign in" : "登录"}</h2>

          {error && (
            <div className="mb-4 rounded-lg bg-warning-soft p-3 text-sm text-warning">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-ink-secondary">{en ? "Username or email" : "用户名或邮箱"}</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="ui-input w-full px-4 py-2.5 text-sm"
                placeholder={en ? "Username or email" : "用户名或邮箱"}
              />
            </div>
            <div>
              <div className="mb-1.5 flex items-center justify-between"><label className="text-sm font-medium text-ink-secondary">{en ? "Password" : "密码"}</label><Link href="/auth/forgot-password" className="ui-link text-xs">{en ? "Forgot password?" : "忘记密码？"}</Link></div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="ui-input w-full px-4 py-2.5 text-sm"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="ui-button-primary w-full"
            >
              {loading ? (en ? "Signing in..." : "登录中...") : (en ? "Sign in" : "登录")}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-ink-muted">{en ? "Access is limited to accounts issued by an administrator." : "仅支持管理员开通的内测账号。"}</p>
        </div>
      </div>
    </div>
  )
}

function returnPath() {
  const requested = new URLSearchParams(window.location.search).get("next")
  return requested?.startsWith("/") && !requested.startsWith("//") ? requested : "/"
}
