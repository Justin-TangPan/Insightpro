"use client";

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { usePreferences } from "@/lib/preferences";
import { EmailSubscriptionManager } from "@/app/settings/_components/email-subscription-manager";

type Delivery = { subscriber_id: number; recipient_email: string; delivery_date: string; delivery_type: string; status: string; attempts: number; last_error?: string; sent_at?: string; updated_at: string };

export default function AdminEmailsPage() {
  const { user, loading } = useAuth();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [items, setItems] = useState<Delivery[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      const response = await authenticatedFetch(API + "/api/v2/admin/email-deliveries?limit=200");
      if (!response.ok) throw new Error(en ? "Could not load email deliveries." : "邮件投递记录加载失败。");
      setItems((await response.json()).items || []);
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Error"); }
  }, [en]);
  useEffect(() => { if (user?.app_metadata?.role === "admin") void Promise.resolve().then(load); }, [load, user]);
  if (loading) return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Checking access…" : "正在验证权限…"}</div>;
  if (user?.app_metadata?.role !== "admin") return <div className="ui-card py-12 text-center text-sm text-ink-muted">{en ? "Administrator access required." : "需要管理员权限。"}</div>;
  return <div className="page-stack">
    <SectionHeader badge="Admin / Email" title={en ? "Email" : "邮件管理"} subtitle={en ? "Manage subscribers and review brief delivery." : "管理订阅用户，查看商业与技术简报投递记录。"} action={<button className="ui-button-secondary" onClick={() => void load()}><RefreshCw size={15} />{en ? "Refresh" : "刷新"}</button>} />
    {error && <div role="status" className="ui-card text-sm text-danger">{error}</div>}
    <EmailSubscriptionManager />
    <section className="ui-card overflow-x-auto"><table className="w-full min-w-[760px] text-left text-xs"><thead className="text-ink-muted"><tr><th className="py-2">{en ? "Recipient" : "收件人"}</th><th>{en ? "Date" : "日期"}</th><th>{en ? "Brief" : "简报"}</th><th>{en ? "Status" : "状态"}</th><th>{en ? "Attempts" : "尝试次数"}</th><th>{en ? "Last error" : "最近错误"}</th></tr></thead><tbody>{items.map((item, index) => <tr key={`${item.subscriber_id}-${item.delivery_date}-${item.delivery_type}-${index}`} className="border-t border-grid"><td className="py-2.5">{item.recipient_email}</td><td className="font-mono">{item.delivery_date}</td><td>{item.delivery_type === "business" ? (en ? "Business" : "商业洞察") : (en ? "Technical" : "技术项目")}</td><td><span className={`ui-tag ${item.status === "sent" ? "ui-tag-success" : "ui-tag-danger"}`}>{item.status}</span></td><td className="font-mono">{item.attempts}</td><td className="max-w-72 truncate text-danger">{item.last_error || "—"}</td></tr>)}</tbody></table>{!items.length && !error && <p className="py-10 text-center text-sm text-ink-muted">{en ? "No delivery attempts yet." : "暂无投递记录。"}</p>}</section>
  </div>;
}
