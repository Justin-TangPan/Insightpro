"use client";

import { SectionHeader } from "@/components/section-header";
import { useState, useEffect } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { Save, RefreshCw, Bell, Database, Shield, User, Mail, Send, Plus, Trash2, CheckCircle2, Eye, X, Clock3 } from "lucide-react";

interface Subscriber {
  id: number;
  email: string;
  name: string;
  active: number;
  weekdays: number[];
  send_time: string;
}

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

export default function SettingsPage() {
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

  const handleSave = () => {
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
    void Promise.resolve().then(fetchSubscribers);
    fetch(`${API}/api/system/health/ready`)
      .then((res) => res.json())
      .then((report) => setDatabaseConnected(report.checks?.database === true))
      .catch(() => setDatabaseConnected(false));
  }, []);

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
    <div className="space-y-8">
      <SectionHeader
        badge="Settings"
        title="系统设置"
        subtitle="管理平台配置、通知偏好、邮件订阅和数据源连接"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Profile */}
        <div className="rounded-lg bg-white border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
            <User className="h-4 w-4 text-ink-muted" />
            <h3 className="font-semibold text-sm text-ink">用户信息</h3>
          </div>
          <div className="space-y-3.5">
            <div>
              <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">用户名</label>
              <input type="text" defaultValue="Justin Tang" className="w-full px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors" />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">邮箱</label>
              <input type="email" defaultValue="1315304560@qq.com" className="w-full px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[13px] text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors" />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">套餐</label>
              <div className="px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[13px] font-semibold text-ink flex items-center gap-2">
                Premium Plan
                <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 text-[10px] font-semibold">Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Notification */}
        <div className="rounded-lg bg-white border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
            <Bell className="h-4 w-4 text-ink-muted" />
            <h3 className="font-semibold text-sm text-ink">通知设置</h3>
          </div>
          <div className="space-y-0.5">
            {notifications.map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2.5 border-b border-slate-100 last:border-0">
                <div>
                  <p className="text-sm font-medium text-ink">{item.label}</p>
                  <p className="text-xs text-ink-muted mt-0.5">{item.desc}</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleToggle(i)}
                  className={`relative w-9 h-5 rounded-full cursor-pointer transition-colors ${toggles[i] ? "bg-slate-900" : "bg-slate-200"}`}
                >
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${toggles[i] ? "translate-x-[18px]" : "translate-x-0.5"}`} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Email Subscription */}
        <div className="rounded-lg bg-white border border-slate-200/80 p-5 shadow-sm lg:col-span-2">
          <div className="mb-4 flex flex-col gap-3 border-b border-slate-100 pb-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2.5">
              <Mail className="h-4 w-4 text-ink-muted" />
              <h3 className="serif-heading text-sm text-ink">邮件订阅管理</h3>
              <span className="text-[10px] font-medium text-ink-muted">每位订阅者独立排期</span>
            </div>
            <div className="flex gap-2 self-start">
              <button
                onClick={handlePreview}
                disabled={previewing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900 text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
              >
                <Eye className="h-3 w-3" />
                {previewing ? "生成中..." : "预览邮件"}
              </button>
            </div>
          </div>

          {/* Add subscriber */}
          <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50/70 p-3.5">
            <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_9rem_auto]">
              <input
                type="email"
                aria-label="收件人邮箱"
                placeholder="收件人邮箱"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-[13px] text-ink outline-none transition-colors focus:border-slate-400"
              />
              <input
                type="text"
                aria-label="订阅者姓名"
                placeholder="姓名（可选）"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-[13px] text-ink outline-none transition-colors focus:border-slate-400"
              />
              <button
                onClick={handleSubscribe}
                disabled={!newEmail || !newWeekdays.length}
                className="flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
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
                    className={`h-7 w-7 rounded-md text-[11px] font-semibold transition-colors ${newWeekdays.includes(day) ? "bg-slate-900 text-white" : "border border-slate-200 bg-white text-ink-muted hover:border-slate-300"}`}
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
                  className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-ink outline-none focus:border-slate-400"
                />
              </label>
            </div>
          </div>

          {emailStatus && (
            <div role="status" className={`mb-4 flex items-center gap-2 rounded-lg border px-3 py-2 ${emailError ? "border-rose-200 bg-rose-50" : "border-emerald-200 bg-emerald-50"}`}>
              <CheckCircle2 className={`h-3.5 w-3.5 ${emailError ? "text-rose-600" : "text-emerald-600"}`} />
              <span className={`text-xs ${emailError ? "text-rose-700" : "text-emerald-700"}`}>{emailStatus}</span>
            </div>
          )}

          {/* Subscriber list */}
          <div className="space-y-2">
            {subscribers.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-sm text-ink-muted">{subscriberError || "暂无订阅者"}</p>
                {subscriberError && (
                  <a href="/auth/login" className="mt-2 inline-flex rounded-xl bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">
                    登录后查看订阅者
                  </a>
                )}
              </div>
            ) : (
              subscribers.map((sub) => (
                <div key={sub.id} className="rounded-xl border border-slate-200 px-3.5 py-3 transition-colors hover:border-slate-300">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex min-w-0 items-center gap-3 lg:w-64">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-ink-muted">
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
                          className={`h-7 w-7 rounded-md text-[11px] font-semibold transition-colors ${sub.weekdays.includes(day) ? "bg-emerald-700 text-white" : "border border-slate-200 text-ink-muted hover:border-slate-300"}`}
                        >
                          {label}
                        </button>
                      ))}
                      <input
                        type="time"
                        aria-label={`${sub.email} 投递时间`}
                        value={sub.send_time}
                        onChange={(e) => updateSubscriberDraft(sub.id, { send_time: e.target.value })}
                        className="ml-1 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-ink outline-none focus:border-slate-400"
                      />
                    </div>

                    <div className="flex items-center gap-1.5 self-end lg:self-auto">
                      <button
                        onClick={() => handleUpdateSubscriber(sub)}
                        disabled={savingId === sub.id}
                        className="rounded-md border border-slate-200 px-2.5 py-1.5 text-[11px] font-semibold text-ink-secondary transition-colors hover:bg-slate-50 disabled:opacity-50"
                      >
                        {savingId === sub.id ? "保存中" : "保存排期"}
                      </button>
                      <button
                        onClick={() => handleSendSubscriber(sub)}
                        disabled={sendingId === sub.id}
                        className="flex items-center gap-1 rounded-md bg-slate-900 px-2.5 py-1.5 text-[11px] font-semibold text-white transition-colors hover:bg-slate-800 disabled:opacity-50"
                      >
                        <Send className="h-3 w-3" />
                        {sendingId === sub.id ? "发送中" : "立即发送"}
                      </button>
                      <button
                        onClick={() => handleRemove(sub.email)}
                        className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-rose-50 hover:text-rose-500"
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
        <div className="rounded-lg bg-white border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
            <Database className="h-4 w-4 text-ink-muted" />
            <h3 className="font-semibold text-sm text-ink">数据源配置</h3>
          </div>
          <div className="space-y-0.5">
            {dataSources.map((src, i) => (
              <div key={i} className="flex items-center justify-between py-2.5 border-b border-slate-100 last:border-0">
                <span className="text-sm font-medium text-ink">{src.name}</span>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${src.ok ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"}`}>
                  {src.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Security */}
        <div className="rounded-lg bg-white border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
            <Shield className="h-4 w-4 text-ink-muted" />
            <h3 className="font-semibold text-sm text-ink">安全设置</h3>
          </div>
          <div className="space-y-3.5">
            <div>
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">API Key</label>
              <input type="password" defaultValue="••••••••" disabled className="w-full px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[13px] font-mono text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors" />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">数据库连接</label>
              <input type="password" defaultValue="postgresql://••••••••" disabled className="w-full px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[13px] font-mono text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors" />
            </div>
          </div>
        </div>
      </div>

      {previewHtml && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="邮件预览">
          <div className="flex h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
              <div>
                <h2 className="text-sm font-semibold text-ink">每日洞察邮件预览</h2>
                <p className="text-xs text-ink-muted">以下内容与正式发送版本一致</p>
              </div>
              <button onClick={() => setPreviewHtml("")} className="rounded-lg p-2 text-ink-muted hover:bg-slate-100 hover:text-ink" aria-label="关闭邮件预览">
                <X className="h-4 w-4" />
              </button>
            </div>
            <iframe title="每日洞察邮件" srcDoc={previewHtml} sandbox="" className="min-h-0 flex-1 bg-slate-100" />
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="flex items-center gap-2 rounded-lg bg-slate-900 px-6 py-2.5 text-[13px] font-semibold text-white hover:bg-slate-800 transition-colors"
        >
          {saved ? <><RefreshCw className="h-4 w-4" /> 已保存</> : <><Save className="h-4 w-4" /> 保存设置</>}
        </button>
      </div>
    </div>
  );
}
