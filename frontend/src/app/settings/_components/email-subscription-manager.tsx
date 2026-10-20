"use client";

import { useState, useEffect, useMemo } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import { Mail, Eye, Clock3, Plus, Send, Trash2, CheckCircle2, Search } from "lucide-react";
import { AppDialog } from "@/components/ui";
import type { Subscriber } from "./types";

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];
const EN_WEEKDAYS = ["M", "T", "W", "T", "F", "S", "S"];

function DeliveryTimePicker({ value, onChange, label = "投递时间" }: { value: string; onChange: (value: string) => void; label?: string }) {
  return <div className="ml-1 flex flex-wrap items-center gap-1.5"><input type="time" aria-label={label} value={value} onChange={event => onChange(event.target.value)} step="300" className="ui-input px-2.5 py-1.5 text-xs" />{["09:00", "12:00", "18:00"].map(time => <button key={time} type="button" onClick={() => onChange(time)} aria-pressed={value === time} className={`min-h-8 rounded-md px-2 text-[10px] font-semibold ${value === time ? "bg-primary text-white" : "border border-grid bg-white text-ink-muted hover:border-primary/30"}`}>{time}</button>)}</div>;
}

export function EmailSubscriptionManager() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const t = (zh: string, english: string) => en ? english : zh;
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";

  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [subscriberError, setSubscriberError] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newWeekdays, setNewWeekdays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [newSendTime, setNewSendTime] = useState("09:05");
  const [newLanguage, setNewLanguage] = useState<Subscriber["language"]>(preferences.language);
  const [emailStatus, setEmailStatus] = useState("");
  const [emailError, setEmailError] = useState(false);
  const [sendingId, setSendingId] = useState<number | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [previewHtml, setPreviewHtml] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const [subscriberQuery, setSubscriberQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [subscriberPage, setSubscriberPage] = useState(1);
  const pageSize = 25;

  const filteredSubscribers = useMemo(() => {
    const query = subscriberQuery.trim().toLowerCase();
    return subscribers.filter(sub => !query || sub.email.toLowerCase().includes(query) || sub.name.toLowerCase().includes(query));
  }, [subscriberQuery, subscribers]);
  const pageCount = Math.max(1, Math.ceil(filteredSubscribers.length / pageSize));
  const visibleSubscribers = filteredSubscribers.slice((subscriberPage - 1) * pageSize, subscriberPage * pageSize);
  const visibleIds = visibleSubscribers.map(sub => sub.id);
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every(id => selectedIds.includes(id));

  const fetchSubscribers = async () => {
    try {
      const res = await authenticatedFetch(`${API}/api/email/subscribers`);
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      const data = await res.json();
      setSubscribers((data.subscribers || []).map((subscriber: Subscriber) => ({
        ...subscriber,
        weekdays: subscriber.weekdays?.length ? subscriber.weekdays : [0, 1, 2, 3, 4, 5, 6],
        send_time: subscriber.send_time || "09:05",
        language: subscriber.language === "en" ? "en" : "zh",
      })));
      setSelectedIds([]);
      setSubscriberPage(1);
      setSubscriberError("");
    } catch (err) {
      console.error("Failed to fetch subscribers:", err);
      setSubscriberError(err instanceof Error ? err.message : t("订阅者加载失败", "Could not load subscribers"));
    }
  };

  const handleSubscribe = async () => {
    if (!newEmail) return;
    try {
      const res = await authenticatedFetch(`${API}/api/email/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: newEmail, name: newName, weekdays: newWeekdays, send_time: newSendTime, language: newLanguage }),
      });
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      await res.json();
      setEmailStatus(t("订阅成功", "Subscription added"));
      setEmailError(false);
      setNewEmail("");
      setNewName("");
      fetchSubscribers();
      setTimeout(() => setEmailStatus(""), 3000);
    } catch {
      setEmailStatus(t("订阅失败", "Subscription failed"));
      setEmailError(true);
    }
  };

  const handleRemove = async (email: string) => {
    try {
      await authenticatedFetch(`${API}/api/email/subscribers/${encodeURIComponent(email)}`, { method: "DELETE" });
      fetchSubscribers();
    } catch (err) {
      console.error("Failed to remove subscriber:", err);
    }
  };

  const handleBulkRemove = async () => {
    if (!selectedIds.length) return;
    await Promise.all(selectedIds.map(id => {
      const subscriber = subscribers.find(item => item.id === id);
      return subscriber ? authenticatedFetch(`${API}/api/email/subscribers/${encodeURIComponent(subscriber.email)}`, { method: "DELETE" }) : Promise.resolve();
    }));
    setSelectedIds([]);
    await fetchSubscribers();
    setEmailStatus(t(`已停用 ${selectedIds.length} 位订阅者`, `Disabled ${selectedIds.length} subscribers`));
    setEmailError(false);
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
        body: JSON.stringify({ weekdays: subscriber.weekdays, send_time: subscriber.send_time, language: subscriber.language }),
      });
      if (!res.ok) { throw new Error(`API error: ${res.status}`); }
      await res.json();
      setEmailStatus(t("排期已保存", "Schedule saved"));
      setEmailError(false);
    } catch {
      setEmailStatus(t("投递计划保存失败", "Could not save delivery schedule"));
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
      await res.json();
      setEmailStatus(t("已发送", "Email sent"));
      setEmailError(false);
    } catch {
      setEmailStatus(t("发送失败，请检查 SMTP 配置", "Send failed. Check SMTP settings."));
      setEmailError(true);
    } finally {
      setSendingId(null);
    }
  };

  const handlePreview = async () => {
    setPreviewing(true);
    setEmailStatus("");
    try {
      const res = await authenticatedFetch(`${API}/api/email/preview?language=${preferences.language}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      setPreviewHtml(await res.text());
    } catch {
      setEmailStatus(t("预览生成失败，请稍后重试", "Could not generate preview. Try again later."));
      setEmailError(true);
    } finally {
      setPreviewing(false);
    }
  };

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    const timer = window.setTimeout(() => void fetchSubscribers(), 0);
    return () => window.clearTimeout(timer);
  }, [authLoading, isAdmin]);

  return (
    <>
      <div className="ui-card lg:col-span-2">
        <div className="ui-card-header flex-col sm:flex-row sm:items-center">
          <div className="flex items-center gap-2.5">
            <Mail className="h-4 w-4 text-ink-muted" />
            <h3 className="type-h3 text-ink">{t("邮件订阅管理", "Email subscriptions")}</h3>
            <span className="text-[10px] font-medium text-ink-muted">{t("每位订阅者独立排期", "Schedule each subscriber separately")}</span>
          </div>
          <div className="flex gap-2 self-start">
            <button
              onClick={handlePreview}
              disabled={previewing}
              className="ui-button-secondary"
            >
              <Eye className="h-3 w-3" />
              {previewing ? t("生成中...", "Generating...") : t("预览邮件", "Preview email")}
            </button>
          </div>
        </div>

        {/* Add subscriber */}
        <div className="mb-4 rounded-xl bg-surface-subtle p-4">
          <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_9rem_auto]">
            <input
              type="email"
              aria-label={t("收件人邮箱", "Recipient email")}
              placeholder={t("收件人邮箱", "Recipient email")}
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="ui-input px-3.5 py-2 text-[13px]"
            />
            <input
              type="text"
              aria-label={t("订阅者姓名", "Subscriber name")}
              placeholder={t("姓名（可选）", "Name (optional)")}
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
              {t("添加订阅", "Add subscriber")}
            </button>
          </div>
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-1.5" aria-label={t("新订阅投递星期", "New subscriber delivery weekdays")}>
              <span className="mr-1 text-[10px] font-semibold uppercase tracking-wider text-ink-muted">{t("每周", "Weekly")}</span>
              {(en ? EN_WEEKDAYS : WEEKDAYS).map((label, day) => (
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
              {t("投递时间", "Delivery time")}
              <DeliveryTimePicker value={newSendTime} onChange={setNewSendTime} label={t("投递时间", "Delivery time")} />
            </label>
            <label className="flex items-center gap-2 text-xs font-medium text-ink-secondary">{t("邮件语言", "Email language")}<select value={newLanguage} onChange={event => setNewLanguage(event.target.value as Subscriber["language"])} className="ui-input px-2.5 py-1.5 text-xs"><option value="zh">简体中文</option><option value="en">English</option></select></label>
          </div>
        </div>

        {emailStatus && (
          <div role="status" className={`mb-4 flex items-center gap-2 rounded-lg border px-3 py-2 ${emailError ? "border-warning/20 bg-warning-soft" : "border-primary/20 bg-primary-soft"}`}>
            <CheckCircle2 className={`h-3.5 w-3.5 ${emailError ? "text-warning" : "text-primary"}`} />
            <span className={`text-xs ${emailError ? "text-warning" : "text-primary"}`}>{emailStatus}</span>
          </div>
        )}

        {/* Subscriber list */}
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="relative min-w-[220px] flex-1 sm:max-w-sm"><Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-muted" /><input value={subscriberQuery} onChange={event => { setSubscriberQuery(event.target.value); setSubscriberPage(1); }} placeholder={t("搜索邮箱或姓名", "Search email or name")} aria-label={t("搜索订阅者", "Search subscribers")} className="ui-input w-full pl-9 pr-3 py-2 text-xs" /></div>
          <div className="flex items-center gap-2 text-xs text-ink-muted"><span>{filteredSubscribers.length}/{subscribers.length}</span><button type="button" onClick={() => setSelectedIds(allVisibleSelected ? selectedIds.filter(id => !visibleIds.includes(id)) : [...new Set([...selectedIds, ...visibleIds])])} className="ui-button-secondary !min-h-8 !px-2.5 !py-1.5">{allVisibleSelected ? t("取消全选", "Clear page") : t("选择本页", "Select page")}</button>{selectedIds.length > 0 && <button type="button" onClick={() => void handleBulkRemove()} className="ui-button-danger !min-h-8 !px-2.5 !py-1.5">{t(`批量停用 (${selectedIds.length})`, `Disable selected (${selectedIds.length})`)}</button>}</div>
        </div>
        <div className="space-y-2">
          {subscribers.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-sm text-ink-muted">{subscriberError || t("暂无订阅者", "No subscribers yet")}</p>
              {subscriberError && (
                <a href="/auth/login" className="mt-2 inline-flex rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-white">
                  {t("登录后查看订阅者", "Sign in to view subscribers")}
                </a>
              )}
            </div>
          ) : (
            visibleSubscribers.map((sub) => (
              <div key={sub.id} className="rounded-xl bg-surface-subtle/70 px-4 py-3.5 transition-colors hover:bg-primary-soft/60">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div className="flex min-w-0 items-center gap-2 lg:w-64"><input type="checkbox" checked={selectedIds.includes(sub.id)} onChange={() => setSelectedIds(ids => ids.includes(sub.id) ? ids.filter(id => id !== sub.id) : [...ids, sub.id])} aria-label={`${t("选择", "Select")} ${sub.email}`} className="h-4 w-4 accent-[var(--color-primary)]" />
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-subtle text-[10px] font-bold text-ink-muted">
                      {(sub.name || sub.email)[0].toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-[13px] font-medium text-ink">{sub.email}</p>
                      <p className="text-[10px] text-ink-muted">{sub.name || t("未填写姓名", "No name")}</p>
                    </div>
                  </div></div>

                  <div className="flex flex-1 flex-wrap items-center gap-1.5" aria-label={`${sub.email} ${t("投递星期", "delivery weekdays")}`}>
                    {(en ? EN_WEEKDAYS : WEEKDAYS).map((label, day) => (
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
                    <DeliveryTimePicker value={sub.send_time} onChange={(send_time) => updateSubscriberDraft(sub.id, { send_time })} label={`${sub.email} ${t("投递时间", "delivery time")}`} />
                    <select aria-label={`${sub.email} ${t("邮件语言", "email language")}`} value={sub.language || "zh"} onChange={event => updateSubscriberDraft(sub.id, { language: event.target.value as Subscriber["language"] })} className="ui-input px-2 py-1.5 text-xs"><option value="zh">中文</option><option value="en">English</option></select>
                  </div>

                  <div className="flex items-center gap-1.5 self-end lg:self-auto">
                    <button
                      onClick={() => handleUpdateSubscriber(sub)}
                      disabled={savingId === sub.id}
                      className="ui-button-secondary !min-h-8 !px-2.5 !py-1.5 text-[11px]"
                    >
                      {savingId === sub.id ? t("保存中", "Saving") : t("保存排期", "Save schedule")}
                    </button>
                    <button
                      onClick={() => handleSendSubscriber(sub)}
                      disabled={sendingId === sub.id}
                      className="ui-button-primary !min-h-8 !px-2.5 !py-1.5 text-[11px]"
                    >
                      <Send className="h-3 w-3" />
                      {sendingId === sub.id ? t("发送中", "Sending") : t("立即发送", "Send now")}
                    </button>
                    <button
                      onClick={() => handleRemove(sub.email)}
                      className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-warning-soft hover:text-warning"
                      aria-label={`${t("删除", "Remove")} ${sub.email}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
        {filteredSubscribers.length > pageSize && <div className="mt-4 flex items-center justify-between text-xs text-ink-muted"><span>{t(`第 ${subscriberPage}/${pageCount} 页`, `Page ${subscriberPage} of ${pageCount}`)}</span><div className="flex gap-2"><button type="button" disabled={subscriberPage === 1} onClick={() => setSubscriberPage(page => page - 1)} className="ui-button-secondary !min-h-8 !px-3 !py-1.5">{t("上一页", "Previous")}</button><button type="button" disabled={subscriberPage === pageCount} onClick={() => setSubscriberPage(page => page + 1)} className="ui-button-secondary !min-h-8 !px-3 !py-1.5">{t("下一页", "Next")}</button></div></div>}
      </div>

      <AppDialog open={!!previewHtml} onClose={() => setPreviewHtml("")} title={t("每日洞察邮件预览", "Daily insights email preview")} description={t("以下内容与正式发送版本一致", "This is the same content subscribers will receive")} className="h-[92dvh] w-[min(80rem,calc(100vw-2rem))] max-w-none overflow-hidden">
        <iframe title={t("每日洞察邮件", "Daily insights email")} srcDoc={previewHtml} sandbox="" className="h-[calc(92dvh-8rem)] w-full bg-surface-subtle" />
      </AppDialog>
    </>
  );
}
