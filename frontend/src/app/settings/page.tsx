"use client";

import { SectionHeader } from "@/components/section-header";
import { useState, useEffect } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences, type Preferences } from "@/lib/preferences";
import { Save, RefreshCw, Bell, Database, Shield, User, Mail, Send, Plus, Trash2, CheckCircle2, Eye, X, Clock3, Palette, Languages, Users, SlidersHorizontal, Bot } from "lucide-react";
import Link from "next/link";

interface Subscriber {
  id: number;
  email: string;
  name: string;
  active: number;
  weekdays: number[];
  send_time: string;
}

interface AccountUser {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
  last_sign_in_at: string | null;
}

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

export default function SettingsPage() {
  const { user, loading: authLoading, updateProfile } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";
  const { preferences, updatePreferences } = usePreferences();
  const [profileName, setProfileName] = useState("");
  const [users, setUsers] = useState<AccountUser[]>([]);
  const [saved, setSaved] = useState(false);
  const [toggles, setToggles] = useState(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("notification_toggles");
        if (saved) return JSON.parse(saved);
      } catch {}
    }
    return [true, true, true, false];
  });
  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [subscriberError, setSubscriberError] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newWeekdays, setNewWeekdays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [newSendTime, setNewSendTime] = useState("09:05");
  const [emailStatus, setEmailStatus] = useState("");
  const [emailError, setEmailError] = useState(false);
  const [sendingId, setSendingId] = useState<number | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [databaseConnected, setDatabaseConnected] = useState(false);
  const [previewHtml, setPreviewHtml] = useState("");
  const [previewing, setPreviewing] = useState(false);

  const handleSave = async () => {
    if (user && profileName !== (user.user_metadata?.name || "")) await updateProfile(profileName);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleToggle = (index: number) => {
    setToggles((prev: boolean[]) => {
      const next = prev.map((v, i) => (i === index ? !v : v));
      try { localStorage.setItem("notification_toggles", JSON.stringify(next)); } catch {}
      return next;
    });
  };

  // Fetch subscribers
  const fetchSubscribers = async () => {
    try {
      const res = await authenticatedFetch(`${API}/api/email/subscribers`);
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      const data = await res.json();
      setSubscribers((data.subscribers || []).map((subscriber: Subscriber) => ({
        ...subscriber,
        weekdays: subscriber.weekdays?.length ? subscriber.weekdays : [0, 1, 2, 3, 4, 5, 6],
        send_time: subscriber.send_time || "09:05",
      })));
      setSubscriberError("");
    } catch (err) {
      console.error("Failed to fetch subscribers:", err);
      setSubscriberError(err instanceof Error ? err.message : "订阅者加载失败");
    }
  };

  useEffect(() => {
    if (authLoading) return;
    void Promise.resolve().then(() => setProfileName(user?.user_metadata?.name || ""));
    if (!isAdmin) return;
    void Promise.resolve().then(fetchSubscribers);
    void authenticatedFetch(`${API}/api/auth/users`)
      .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
      .then(data => setUsers(data.users || []))
      .catch(() => setUsers([]));
    fetch(`${API}/api/system/health/ready`)
      .then((res) => res.json())
      .then((report) => setDatabaseConnected(report.checks?.database === true))
      .catch(() => setDatabaseConnected(false));
  }, [authLoading, isAdmin, user]);

  // Add subscriber
  const handleSubscribe = async () => {
    if (!newEmail) return;
    try {
      const res = await authenticatedFetch(`${API}/api/email/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: newEmail, name: newName, weekdays: newWeekdays, send_time: newSendTime }),
      });
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      const data = await res.json();
      setEmailStatus(data.message);
      setEmailError(false);
      setNewEmail("");
      setNewName("");
      fetchSubscribers();
      setTimeout(() => setEmailStatus(""), 3000);
    } catch {
      setEmailStatus("订阅失败");
      setEmailError(true);
    }
  };

  // Remove subscriber
  const handleRemove = async (email: string) => {
    try {
      await authenticatedFetch(`${API}/api/email/subscribers/${encodeURIComponent(email)}`, { method: "DELETE" });
      fetchSubscribers();
    } catch (err) {
      console.error("Failed to remove subscriber:", err);
    }
  };

  const toggleNewWeekday = (day: number) => {
    setNewWeekdays((days) => {
      if (days.includes(day) && days.length === 1) return days;
      return days.includes(day) ? days.filter((item) => item !== day) : [...days, day].sort();
    });
  };

  const updateSubscriberDraft = (id: number, changes: Partial<Subscriber>) => {
    setSubscribers((items) => items.map((item) => item.id === id ? { ...item, ...changes } : item));
  };

  const toggleSubscriberWeekday = (subscriber: Subscriber, day: number) => {
    const weekdays = subscriber.weekdays.includes(day)
      ? subscriber.weekdays.filter((item) => item !== day)
      : [...subscriber.weekdays, day].sort();
    if (weekdays.length) updateSubscriberDraft(subscriber.id, { weekdays });
  };

  const handleUpdateSubscriber = async (subscriber: Subscriber) => {
    setSavingId(subscriber.id);
    try {
      const res = await authenticatedFetch(`${API}/api/email/subscribers/${subscriber.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weekdays: subscriber.weekdays, send_time: subscriber.send_time }),
      });
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      const data = await res.json();
      setEmailStatus(data.message);
      setEmailError(false);
    } catch {
      setEmailStatus("投递计划保存失败");
      setEmailError(true);
    } finally {
      setSavingId(null);
    }
  };

  const handleSendSubscriber = async (subscriber: Subscriber) => {
    setSendingId(subscriber.id);
    try {
      const res = await authenticatedFetch(`${API}/api/email/subscribers/${subscriber.id}/send`, { method: "POST" });
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      const data = await res.json();
      setEmailStatus(data.message);
      setEmailError(false);
    } catch {
      setEmailStatus("发送失败，请检查 SMTP 配置");
      setEmailError(true);
    } finally {
      setSendingId(null);
    }
  };

  const handlePreview = async () => {
    setPreviewing(true);
    setEmailStatus("");
    try {
      const res = await authenticatedFetch(`${API}/api/email/preview`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setPreviewHtml(await res.text());
    } catch {
      setEmailStatus("预览生成失败，请稍后重试");
      setEmailError(true);
    } finally {
      setPreviewing(false);
    }
  };

  const notifications = [
    { label: "每日洞察日报", desc: "按订阅者配置的星期和时间推送" },
    { label: "友商动态预警", desc: "友商有重大动态时实时推送" },
    { label: "解决方案更新", desc: "技术方案新增或发生变化时推送" },
    { label: "系统异常告警", desc: "API 或数据源异常时推送" },
  ];

  const dataSources = [
    { name: "GitHub Trending", status: "已连接", ok: true },
    { name: "百度热搜", status: "已连接", ok: true },
    { name: "DeepSeek AI", status: "已连接", ok: true },
    { name: "Supabase", status: databaseConnected ? "已连接" : "未连接", ok: databaseConnected },
  ];

  return (
    <div className="page-stack">
      <SectionHeader
        badge="Settings"
        title={preferences.language === "en" ? "System Settings" : "系统设置"}
        subtitle={preferences.language === "en" ? "Manage your account, appearance and preferences" : "管理账号、外观与使用偏好"}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Profile */}
        <div className="ui-card">
          <div className="ui-card-header">
            <User className="h-4 w-4 text-ink-muted" />
            <h3 className="type-h3 text-ink">用户信息</h3>
          </div>
          <div className="space-y-3.5">
            <div>
              <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">用户名</label>
              <input type="text" value={profileName} onChange={event => setProfileName(event.target.value)} className="ui-input w-full px-3.5 py-2 text-sm" />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">邮箱</label>
              <input type="email" value={user?.email || ""} disabled className="ui-input w-full bg-surface-subtle px-3.5 py-2 text-[13px]" />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">套餐</label>
              <div className="px-3.5 py-2 rounded-lg border border-grid bg-surface-subtle text-[13px] font-semibold text-ink flex items-center gap-2">
                InsightPro
                <span className="ui-tag">{isAdmin ? "Admin" : "User"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Notification */}
        <div className="ui-card">
          <div className="ui-card-header">
            <Bell className="h-4 w-4 text-ink-muted" />
            <h3 className="type-h3 text-ink">通知设置</h3>
          </div>
          <div className="space-y-0.5">
            {notifications.map((item, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg px-3 py-2.5 odd:bg-surface-subtle/60">
                <div>
                  <p className="text-sm font-medium text-ink">{item.label}</p>
                  <p className="text-xs text-ink-muted mt-0.5">{item.desc}</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleToggle(i)}
                  className={`relative w-9 h-5 rounded-full cursor-pointer transition-colors ${toggles[i] ? "bg-primary" : "bg-grid"}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${toggles[i] ? "translate-x-[18px]" : "translate-x-0.5"}`} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Appearance */}
        <div className="ui-card lg:col-span-2">
          <div className="ui-card-header">
            <div className="flex items-center gap-2.5"><Palette className="h-4 w-4 text-ink-muted" /><h3 className="type-h3 text-ink">{preferences.language === "en" ? "Appearance & Preferences" : "外观与偏好"}</h3></div>
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <label className="mb-2 flex items-center gap-2 text-xs font-semibold text-ink-muted"><Palette className="h-3.5 w-3.5" />{preferences.language === "en" ? "Theme color" : "主题色"}</label>
              <div className="flex flex-wrap gap-2">
                {([[
                  "green", "经典绿", "#176b46"
                ], ["mono", "极简黑白", "#18181b"], ["orange", "暖橙", "#c15f2b"], ["blue", "商务蓝", "#2563eb"], ["purple", "科技紫", "#7c3aed"]] as [Preferences["theme"], string, string][]).map(([value, label, color]) => (
                  <button key={value} type="button" aria-pressed={preferences.theme === value} onClick={() => updatePreferences({ theme: value })} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${preferences.theme === value ? "bg-primary-soft text-primary ring-1 ring-primary/30" : "bg-surface-subtle text-ink-secondary"}`}>
                    <span className="h-3.5 w-3.5 rounded-full" style={{ backgroundColor: color }} />{label}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <label className="text-xs font-semibold text-ink-muted"><span className="mb-2 flex items-center gap-2"><Languages className="h-3.5 w-3.5" />{preferences.language === "en" ? "Language" : "语言"}</span><select value={preferences.language} onChange={event => updatePreferences({ language: event.target.value as Preferences["language"] })} className="ui-input w-full px-3 text-sm"><option value="zh">简体中文</option><option value="en">English</option></select></label>
              <label className="text-xs font-semibold text-ink-muted"><span className="mb-2 flex items-center gap-2"><SlidersHorizontal className="h-3.5 w-3.5" />{preferences.language === "en" ? "Density" : "界面密度"}</span><select value={preferences.density} onChange={event => updatePreferences({ density: event.target.value as Preferences["density"] })} className="ui-input w-full px-3 text-sm"><option value="comfortable">舒适</option><option value="compact">紧凑</option></select></label>
              <label className="flex items-end gap-2 pb-2 text-xs font-semibold text-ink-muted"><input type="checkbox" checked={preferences.motion} onChange={event => updatePreferences({ motion: event.target.checked })} className="accent-primary" />{preferences.language === "en" ? "Animations" : "界面动效"}</label>
            </div>
          </div>
        </div>

        {/* Email Subscription */}
        {isAdmin && <>
        <div className="lg:col-span-2 flex items-center gap-3 pt-2"><Shield className="h-5 w-5 text-primary" /><div><h2 className="type-h2 text-ink">管理员设置</h2><p className="text-xs text-ink-muted">仅管理员可见和操作</p></div></div>
        <div className="ui-card lg:col-span-2">
          <div className="ui-card-header flex-col sm:flex-row sm:items-center">
            <div className="flex items-center gap-2.5">
              <Mail className="h-4 w-4 text-ink-muted" />
              <h3 className="type-h3 text-ink">邮件订阅管理</h3>
              <span className="text-[10px] font-medium text-ink-muted">每位订阅者独立排期</span>
            </div>
            <div className="flex gap-2 self-start">
              <button
                onClick={handlePreview}
                disabled={previewing}
                className="ui-button-secondary"
              >
                <Eye className="h-3 w-3" />
                {previewing ? "生成中..." : "预览邮件"}
              </button>
            </div>
          </div>

          {/* Add subscriber */}
          <div className="mb-4 rounded-xl bg-surface-subtle p-4">
            <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_9rem_auto]">
              <input
                type="email"
                aria-label="收件人邮箱"
                placeholder="收件人邮箱"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="ui-input px-3.5 py-2 text-[13px]"
              />
              <input
                type="text"
                aria-label="订阅者姓名"
                placeholder="姓名（可选）"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="ui-input px-3.5 py-2 text-[13px]"
              />
              <button
                onClick={handleSubscribe}
                disabled={!newEmail || !newWeekdays.length}
                className="ui-button-primary"
              >
                <Plus className="h-3.5 w-3.5" />
                添加订阅
              </button>
            </div>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-1.5" aria-label="新订阅投递星期">
                <span className="mr-1 text-[10px] font-semibold uppercase tracking-wider text-ink-muted">每周</span>
                {WEEKDAYS.map((label, day) => (
                  <button
                    key={day}
                    type="button"
                    aria-pressed={newWeekdays.includes(day)}
                    onClick={() => toggleNewWeekday(day)}
                    className={`h-7 w-7 rounded-md text-[11px] font-semibold transition-colors ${newWeekdays.includes(day) ? "bg-primary text-white" : "border border-grid bg-white text-ink-muted hover:border-primary/30"}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <label className="flex items-center gap-2 text-xs font-medium text-ink-secondary">
                <Clock3 className="h-3.5 w-3.5 text-ink-muted" />
                投递时间
                <input
                  type="time"
                  value={newSendTime}
                  onChange={(e) => setNewSendTime(e.target.value)}
                  className="ui-input px-2.5 py-1.5 text-xs"
                />
              </label>
            </div>
          </div>

          {emailStatus && (
            <div role="status" className={`mb-4 flex items-center gap-2 rounded-lg border px-3 py-2 ${emailError ? "border-warning/20 bg-warning-soft" : "border-primary/20 bg-primary-soft"}`}>
              <CheckCircle2 className={`h-3.5 w-3.5 ${emailError ? "text-warning" : "text-primary"}`} />
              <span className={`text-xs ${emailError ? "text-warning" : "text-primary"}`}>{emailStatus}</span>
            </div>
          )}

          {/* Subscriber list */}
          <div className="space-y-2">
            {subscribers.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-sm text-ink-muted">{subscriberError || "暂无订阅者"}</p>
                {subscriberError && (
                  <a href="/auth/login" className="mt-2 inline-flex rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-white">
                    登录后查看订阅者
                  </a>
                )}
              </div>
            ) : (
              subscribers.map((sub) => (
                <div key={sub.id} className="rounded-xl bg-surface-subtle/70 px-4 py-3.5 transition-colors hover:bg-primary-soft/60">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex min-w-0 items-center gap-3 lg:w-64">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-subtle text-[10px] font-bold text-ink-muted">
                        {(sub.name || sub.email)[0].toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-medium text-ink">{sub.email}</p>
                        <p className="text-[10px] text-ink-muted">{sub.name || "未填写姓名"}</p>
                      </div>
                    </div>

                    <div className="flex flex-1 flex-wrap items-center gap-1.5" aria-label={`${sub.email} 投递星期`}>
                      {WEEKDAYS.map((label, day) => (
                        <button
                          key={day}
                          type="button"
                          aria-pressed={sub.weekdays.includes(day)}
                          onClick={() => toggleSubscriberWeekday(sub, day)}
                          className={`h-7 w-7 rounded-md text-[11px] font-semibold transition-colors ${sub.weekdays.includes(day) ? "bg-primary text-white" : "border border-grid text-ink-muted hover:border-primary/30"}`}
                        >
                          {label}
                        </button>
                      ))}
                      <input
                        type="time"
                        aria-label={`${sub.email} 投递时间`}
                        value={sub.send_time}
                        onChange={(e) => updateSubscriberDraft(sub.id, { send_time: e.target.value })}
                        className="ml-1 rounded-md border border-grid bg-white px-2 py-1.5 text-xs text-ink outline-none focus:border-primary/50"
                      />
                    </div>

                    <div className="flex items-center gap-1.5 self-end lg:self-auto">
                      <button
                        onClick={() => handleUpdateSubscriber(sub)}
                        disabled={savingId === sub.id}
                        className="ui-button-secondary !min-h-8 !px-2.5 !py-1.5 text-[11px]"
                      >
                        {savingId === sub.id ? "保存中" : "保存排期"}
                      </button>
                      <button
                        onClick={() => handleSendSubscriber(sub)}
                        disabled={sendingId === sub.id}
                        className="ui-button-primary !min-h-8 !px-2.5 !py-1.5 text-[11px]"
                      >
                        <Send className="h-3 w-3" />
                        {sendingId === sub.id ? "发送中" : "立即发送"}
                      </button>
                      <button
                        onClick={() => handleRemove(sub.email)}
                        className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-warning-soft hover:text-warning"
                        aria-label={`删除 ${sub.email}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Data Sources */}
        <div className="ui-card">
          <div className="ui-card-header">
            <Database className="h-4 w-4 text-ink-muted" />
            <h3 className="type-h3 text-ink">数据源配置</h3>
          </div>
          <div className="space-y-0.5">
            {dataSources.map((src, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg px-3 py-2.5 odd:bg-surface-subtle/60">
                <span className="text-sm font-medium text-ink">{src.name}</span>
                <span className={`ui-tag ${src.ok ? "" : "ui-tag-warning"}`}>
                  {src.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Security */}
        <div className="ui-card">
          <div className="ui-card-header">
            <Shield className="h-4 w-4 text-ink-muted" />
            <h3 className="type-h3 text-ink">安全设置</h3>
          </div>
          <div className="space-y-3.5">
            <div>
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">API Key</label>
              <input type="password" defaultValue="••••••••" disabled className="ui-input w-full bg-surface-subtle px-3.5 py-2 font-mono text-[13px]" />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">数据库连接</label>
              <input type="password" defaultValue="postgresql://••••••••" disabled className="ui-input w-full bg-surface-subtle px-3.5 py-2 font-mono text-[13px]" />
            </div>
          </div>
        </div>

        {/* Users */}
        <div className="ui-card lg:col-span-2">
          <div className="ui-card-header">
            <div className="flex items-center gap-2.5"><Users className="h-4 w-4 text-ink-muted" /><h3 className="type-h3 text-ink">用户系统</h3></div>
            <span className="ui-tag">{users.length} 位用户</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-ink-muted"><tr><th className="px-3 py-2 font-semibold">用户</th><th className="px-3 py-2 font-semibold">角色</th><th className="px-3 py-2 font-semibold">注册时间</th><th className="px-3 py-2 font-semibold">最近登录</th><th className="px-3 py-2 font-semibold">AI 空间</th></tr></thead>
              <tbody>{users.map(account => <tr key={account.id} className="border-t border-grid/60"><td className="px-3 py-3"><p className="font-medium text-ink">{account.name || account.email?.split("@")[0]}</p><p className="text-ink-muted">{account.email}</p></td><td className="px-3 py-3"><span className="ui-tag">{account.role === "admin" ? "管理员" : "用户"}</span></td><td className="px-3 py-3 text-ink-secondary">{new Date(account.created_at).toLocaleDateString("zh-CN")}</td><td className="px-3 py-3 text-ink-secondary">{account.last_sign_in_at ? new Date(account.last_sign_in_at).toLocaleString("zh-CN") : "尚未登录"}</td><td className="px-3 py-3"><Link href={`/insight-agent?target=${account.id}`} className="ui-link inline-flex items-center gap-1"><Bot className="h-3.5 w-3.5" />管理空间</Link></td></tr>)}</tbody>
            </table>
            {!users.length && <p className="py-8 text-center text-sm text-ink-muted">暂无用户数据</p>}
          </div>
        </div>
        </>}
      </div>

      {previewHtml && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="邮件预览">
          <div className="flex h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-grid px-5 py-3">
              <div>
                <h2 className="text-sm font-semibold text-ink">每日洞察邮件预览</h2>
                <p className="text-xs text-ink-muted">以下内容与正式发送版本一致</p>
              </div>
              <button onClick={() => setPreviewHtml("")} className="rounded-lg p-2 text-ink-muted hover:bg-surface-subtle hover:text-ink" aria-label="关闭邮件预览">
                <X className="h-4 w-4" />
              </button>
            </div>
            <iframe title="每日洞察邮件" srcDoc={previewHtml} sandbox="" className="min-h-0 flex-1 bg-surface-subtle" />
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="ui-button-primary px-6"
        >
          {saved ? <><RefreshCw className="h-4 w-4" /> 已保存</> : <><Save className="h-4 w-4" /> 保存设置</>}
        </button>
      </div>
    </div>
  );
}
