"use client"

import { useState } from "react"
import { useAuth } from "@/components/auth-provider"
import Link from "next/link"

export default function RegisterPage() {
  const { signUp } = useAuth()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    const { error: err } = await signUp(email, password, name)
    setLoading(false)
    if (err) {
      setError(err)
    } else {
      setSuccess(true)
    }
  }

  if (success) {
    return (
      <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4">
        <div className="w-full max-w-md text-center">
          <div className="ui-card p-8">
            <div className="mb-4 text-4xl text-primary">&#x2705;</div>
            <h2 className="type-h2 mb-2 text-ink">注册成功</h2>
            <p className="mb-6 text-sm text-ink-muted">
              请查收邮箱确认链接，确认后即可登录。
            </p>
            <Link
              href="/auth/login"
              className="ui-button-primary px-8"
            >
              去登录
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="type-h1 mb-2 text-primary-dark">InsightPro</h1>
          <p className="type-body text-ink-muted">AI 驱动的技术解决方案洞察平台</p>
        </div>

        <div className="ui-card p-8">
          <h2 className="type-h2 mb-6 text-ink">注册</h2>

          {error && (
            <div className="mb-4 rounded-lg bg-warning-soft p-3 text-sm text-warning">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-ink-secondary">姓名</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="ui-input w-full px-4 py-2.5 text-sm"
                placeholder="张三"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-ink-secondary">邮箱</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="ui-input w-full px-4 py-2.5 text-sm"
                placeholder="your@email.com"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-ink-secondary">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="ui-input w-full px-4 py-2.5 text-sm"
                placeholder="至少 6 位"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="ui-button-primary w-full"
            >
              {loading ? "注册中..." : "注册"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-ink-muted">
            已有账号？{" "}
            <Link href="/auth/login" className="ui-link">
              登录
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
