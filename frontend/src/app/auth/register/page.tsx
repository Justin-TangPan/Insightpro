"use client"

import Link from "next/link"

export default function RegisterPage() {
  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center p-4">
      <div className="w-full max-w-md text-center">
        <div className="mb-8"><h1 className="type-h1 mb-2 text-primary-dark">InsightPro</h1><p className="type-body text-ink-muted">AI 驱动的技术解决方案洞察平台</p></div>
        <div className="ui-card p-8">
          <h2 className="type-h2 mb-3 text-ink">团队成员加入</h2>
          <p className="text-sm leading-6 text-ink-secondary">请联系团队管理员发送邀请邮件。通过邮件设置密码后，即可登录 InsightPro 与 Insight-Agent。</p>
          <Link href="/auth/login" className="ui-button-primary mt-6 px-8">返回登录</Link>
        </div>
      </div>
    </div>
  )
}
