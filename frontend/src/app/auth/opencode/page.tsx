"use client";

import { useEffect, useState } from "react";
import { Bot } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

export default function OpenCodeLaunchPage() {
  const { user, loading } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading || !user) return;
    void authenticatedFetch("/api/auth/opencode/ticket", { method: "POST" })
      .then(async (response) => {
        if (!response.ok) throw new Error(response.status === 403 ? "当前账号未获 OpenCode 单实例访问权限" : "OpenCode 授权失败");
        return response.json() as Promise<{ redirect_url: string }>;
      })
      .then(({ redirect_url }) => window.location.replace(redirect_url))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "OpenCode 授权失败"));
  }, [loading, user]);

  return (
    <div className="ui-card mx-auto mt-20 flex max-w-lg flex-col items-center py-12 text-center">
      <Bot className="h-8 w-8 text-primary" />
      <h1 className="mt-4 type-h2 text-ink">正在进入 OpenCode</h1>
      <p className="mt-2 text-sm text-ink-muted">{error || "正在验证 InsightPro 身份并创建短时访问授权…"}</p>
      {error && <Link href="/" className="ui-button-secondary mt-5">返回首页</Link>}
    </div>
  );
}
