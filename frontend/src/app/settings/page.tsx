"use client";

import { SectionHeader } from "@/components/section-header";
import { useState, useEffect } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences, type Preferences } from "@/lib/preferences";
import { Save, RefreshCw, Bell, Database, Shield, User, Mail, Send, Plus, Trash2, CheckCircle2, Eye, X, Clock3, Palette, Languages, Users, SlidersHorizontal, Bot, FileText } from "lucide-react";
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
  status: "active" | "disabled";
  agent_space_status: string;
  created_at: string;
  last_sign_in_at: string | null;
}

interface AgentSpace extends AccountUser {
  runtime_status: "running" | "stopped";
  workspace_status: "ready" | "not_created";
  last_used_at: string | null;
  disk_bytes: number;
}

interface AgentUsage {
  user_id: string;
  runtime_starts: number;
  days: Record<string, { requests?: number; input_tokens?: number; output_tokens?: number }>;
}

interface ArtifactRequest { id: string; title: string; type: string; created_at: string; }

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

export default function SettingsPage({ adminOnly = false }: { adminOnly?: boolean }) {
  const { user, loading: authLoading, updateProfile } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";
  const { preferences, updatePreferences } = usePreferences();
  const [profileName, setProfileName] = useState("");
  const [users, setUsers] = useState<AccountUser[]>([]);
  const [agentSpaces, setAgentSpaces] = useState<AgentSpace[]>([]);
  const [knowledgeFiles, setKnowledgeFiles] = useState<{ path: string; size: number; updated_at: string; managed: boolean }[]>([]);
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeCategory, setKnowledgeCategory] = useState("");
  const [agentSummary, setAgentSummary] = useState({ ai_space_users: 0, active_runtimes: 0, max_active_runtimes: 0, today: { date: "", requests: 0, input_tokens: 0, output_tokens: 0 } });
  const [agentUsage, setAgentUsage] = useState<AgentUsage[]>([]);
  const [artifactRequests, setArtifactRequests] = useState<ArtifactRequest[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<"user" | "admin">("user");
  const [memberStatus, setMemberStatus] = useState("");
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

  const fetchUsers = () => authenticatedFetch(`${API}/api/auth/users`)
    .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
    .then(data => setUsers(data.users || []))
    .catch(() => setUsers([]));

  const fetchAgentSpaces = () => authenticatedFetch(`${API}/api/auth/agent-spaces`)
    .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
    .then(data => { setAgentSpaces(data.spaces || []); setAgentUsage(data.usage || []); setAgentSummary(data); })
    .catch(() => { setAgentSpaces([]); setAgentUsage([]); setAgentSummary({ ai_space_users: 0, active_runtimes: 0, max_active_runtimes: 0, today: { date: "", requests: 0, input_tokens: 0, output_tokens: 0 } }); });

  const fetchKnowledge = (query = knowledgeQuery) => authenticatedFetch(`${API}/api/auth/public-knowledge?query=${encodeURIComponent(query)}`)
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => setKnowledgeFiles(data.files || []))
    .catch(() => setKnowledgeFiles([]));
  const fetchArtifactRequests = () => authenticatedFetch(`${API}/api/agent/admin/artifacts/requests`)
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => setArtifactRequests(data.items || [])).catch(() => setArtifactRequests([]));
  const publishArtifact = async (id: string) => {
    const response = await authenticatedFetch(`${API}/api/agent/admin/artifacts/${id}/publish`, { method: "POST" });
    setMemberStatus(response.ok ? "Artifact 已沉淀到公共知识库" : "Artifact 发布失败"); if (response.ok) { void fetchArtifactRequests(); void fetchKnowledge(); }
  };

  useEffect(() => {
    if (authLoading) return;
    void Promise.resolve().then(() => setProfileName(user?.user_metadata?.name || ""));
    if (!adminOnly || !isAdmin) return;
    void Promise.resolve().then(fetchSubscribers);
    void fetchUsers();
    void fetchAgentSpaces();
    void fetchKnowledge("");
    void fetchArtifactRequests();
    fetch(`${API}/api/system/health/ready`)
      .then((res) => res.json())
      .then((report) => setDatabaseConnected(report.checks?.database === true))
      .catch(() => setDatabaseConnected(false));
  }, [adminOnly, authLoading, isAdmin, user]);

  const inviteMember = async () => {
    setMemberStatus("");
    const response = await authenticatedFetch(`${API}/api/auth/users/invite`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: inviteEmail, name: inviteName, role: inviteRole }) });
    const data = await response.json();
    if (!response.ok) return setMemberStatus(data.detail || "邀请发送失败");
    setInviteEmail(""); setInviteName(""); setInviteRole("user"); setMemberStatus("邀请已发送"); void fetchUsers();
  };

  const updateMember = async (account: AccountUser, changes: { role?: "user" | "admin"; disabled?: boolean }) => {
    setMemberStatus("");
    const response = await authenticatedFetch(`${API}/api/auth/users/${account.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(changes) });
    const data = await response.json();
    if (!response.ok) return setMemberStatus(data.detail || "成员更新失败");
    setUsers(items => items.map(item => item.id === account.id ? data.user : item));
    void fetchAgentSpaces();
  };

  const controlRuntime = async (space: AgentSpace, action: "start" | "stop") => {
    setMemberStatus("");
    const response = await authenticatedFetch(`${API}/api/auth/agent-spaces/${space.id}/${action}`, { method: "POST" });
    if (!response.ok) return setMemberStatus((await response.json()).detail || "Runtime 操作失败");
    setMemberStatus(action === "start" ? "Runtime 已启动" : "Runtime 已停止");
    void fetchAgentSpaces();
  };

  const uploadKnowledge = async (file?: File) => {
    if (!file) return;
    const data = new FormData(); data.append("file", file); data.append("category", knowledgeCategory);
    const response = await authenticatedFetch(`${API}/api/auth/public-knowledge`, { method: "POST", body: data });
    setMemberStatus(response.ok ? "公共知识已上传" : "公共知识上传失败"); if (response.ok) void fetchKnowledge();
  };

  const deleteKnowledge = async (path: string) => {
    if (!window.confirm(`删除公共知识文件「${path}」？`)) return;
    const response = await authenticatedFetch(`${API}/api/auth/public-knowledge?path=${encodeURIComponent(path)}`, { method: "DELETE" });
    setMemberStatus(response.ok ? "公共知识已删除" : "该文件受保护或删除失败"); if (response.ok) void fetchKnowledge();
  };

  const usageDays = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(); date.setUTCDate(date.getUTCDate() - (6 - index));
    return date.toISOString().slice(0, 10);
  });
  const dailyUsage = usageDays.map(date => ({ date, requests: agentUsage.reduce((sum, item) => sum + (item.days[date]?.requests || 0), 0) }));
  const usageRanking = [...agentUsage].sort((a, b) => (b.days[agentSummary.today.date]?.requests || 0) - (a.days[agentSummary.today.date]?.requests || 0)).slice(0, 3);

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
        badge={adminOnly ? "Admin" : "Settings"}
        title={adminOnly ? "平台管理" : (preferences.language === "en" ? "System Settings" : "系统设置")}
        subtitle={adminOnly ? "用户、数据源、安全与邮件订阅管理" : (preferences.language === "en" ? "Manage your account, appearance and preferences" : "管理账号、外观与使用偏好")}
      />

      {adminOnly && !isAdmin ? <div className="ui-card py-12 text-center text-sm text-ink-muted">需要管理员权限。</div> : <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {!adminOnly && <>
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
          <div className="mt-4 border-t border-grid pt-3">
            <Link href="/auth/forgot-password" className="ui-link text-sm">忘记密码或重置密码</Link>
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

        </>}

        {/* Email Subscription */}
        {adminOnly && isAdmin && <>
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
          <div className="mb-4 grid gap-2 rounded-xl bg-surface-subtle p-4 sm:grid-cols-[minmax(0,1fr)_9rem_7rem_auto]">
            <input type="email" value={inviteEmail} onChange={event => setInviteEmail(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder="成员邮箱" />
            <input type="text" value={inviteName} onChange={event => setInviteName(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder="姓名（可选）" />
            <select value={inviteRole} onChange={event => setInviteRole(event.target.value as "user" | "admin")} className="ui-input px-3 py-2 text-sm"><option value="user">普通用户</option><option value="admin">Admin</option></select>
            <button type="button" onClick={() => void inviteMember()} disabled={!inviteEmail} className="ui-button-primary">邀请成员</button>
            {memberStatus && <p role="status" className="sm:col-span-4 text-xs text-ink-muted">{memberStatus}</p>}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-ink-muted"><tr><th className="px-3 py-2 font-semibold">用户</th><th className="px-3 py-2 font-semibold">角色</th><th className="px-3 py-2 font-semibold">状态</th><th className="px-3 py-2 font-semibold">AI 空间</th><th className="px-3 py-2 font-semibold">操作</th></tr></thead>
              <tbody>{users.map(account => <tr key={account.id} className="border-t border-grid/60"><td className="px-3 py-3"><p className="font-medium text-ink">{account.name || account.email?.split("@")[0]}</p><p className="text-ink-muted">{account.email}</p></td><td className="px-3 py-3"><select value={account.role} disabled={account.id === user?.id} onChange={event => void updateMember(account, { role: event.target.value as "user" | "admin" })} className="ui-input px-2 py-1 text-xs"><option value="user">普通用户</option><option value="admin">Admin</option></select></td><td className="px-3 py-3"><span className={`ui-tag ${account.status === "disabled" ? "ui-tag-warning" : ""}`}>{account.status === "disabled" ? "已禁用" : "正常"}</span></td><td className="px-3 py-3 text-ink-secondary">{account.agent_space_status}</td><td className="px-3 py-3"><div className="flex gap-2"><Link href={`/insight-agent?target=${account.id}`} className="ui-link inline-flex items-center gap-1"><Bot className="h-3.5 w-3.5" />管理</Link><button type="button" disabled={account.id === user?.id} onClick={() => void updateMember(account, { disabled: account.status !== "disabled" })} className="ui-link">{account.status === "disabled" ? "恢复" : "禁用"}</button></div></td></tr>)}</tbody>
            </table>
            {!users.length && <p className="py-8 text-center text-sm text-ink-muted">暂无用户数据</p>}
          </div>
        </div>
        <div className="ui-card lg:col-span-2">
          <div className="ui-card-header"><div className="flex items-center gap-2.5"><Bot className="h-4 w-4 text-ink-muted" /><h3 className="type-h3 text-ink">AI Space 管理</h3></div><span className="ui-tag">{agentSummary.active_runtimes} / {agentSummary.max_active_runtimes} Runtime</span></div>
          <div className="mb-4 grid grid-cols-3 gap-3 text-center text-xs"><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">AI Space 用户</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.ai_space_users}</p></div><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">在线 Runtime</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.active_runtimes}</p></div><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">最大并发</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.max_active_runtimes}</p></div></div>
          <div className="mb-4 grid grid-cols-3 gap-3 text-center text-xs"><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">今日 Agent 用户</p><p className="mt-1 text-lg font-semibold text-ink">{agentUsage.filter(item => (item.days[agentSummary.today.date]?.requests || 0) > 0).length}</p></div><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">今日请求</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.today.requests}</p></div><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">今日 Token</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.today.input_tokens + agentSummary.today.output_tokens}</p></div></div>
          <p className="mb-1 text-xs text-ink-muted">近 7 天请求：{dailyUsage.map(item => `${item.date.slice(5)} ${item.requests}`).join(" · ")}</p><p className="mb-3 text-xs text-ink-muted">Token 仅在模型 Provider 返回 usage 时记录；未返回时只统计真实请求。用户排行：{usageRanking.map(item => `${agentSpaces.find(space => space.id === item.user_id)?.email || item.user_id.slice(0, 8)} ${(item.days[agentSummary.today.date]?.requests || 0)} 次`).join(" · ") || "暂无使用数据"}</p>
          <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-ink-muted"><tr><th className="px-3 py-2">成员</th><th className="px-3 py-2">Runtime</th><th className="px-3 py-2">Workspace</th><th className="px-3 py-2">最近使用</th><th className="px-3 py-2">占用</th><th className="px-3 py-2">操作</th></tr></thead><tbody>{agentSpaces.map(space => <tr key={space.id} className="border-t border-grid/60"><td className="px-3 py-3"><p className="font-medium text-ink">{space.name || space.email.split("@")[0]}</p><p className="text-ink-muted">{space.status === "disabled" ? "Agent 已禁用" : space.email}</p></td><td className="px-3 py-3"><span className={`ui-tag ${space.runtime_status === "running" ? "" : "ui-tag-warning"}`}>{space.runtime_status === "running" ? "运行中" : "已停止"}</span></td><td className="px-3 py-3 text-ink-secondary">{space.workspace_status === "ready" ? "已创建" : "未创建"}</td><td className="px-3 py-3 text-ink-secondary">{space.last_used_at ? new Date(space.last_used_at).toLocaleString("zh-CN") : "—"}</td><td className="px-3 py-3 text-ink-secondary">{space.disk_bytes ? `${(space.disk_bytes / 1024 / 1024).toFixed(1)} MB` : "—"}</td><td className="px-3 py-3"><div className="flex gap-2"><Link href={`/insight-agent?target=${space.id}`} className="ui-link">进入</Link><button type="button" disabled={space.status === "disabled" || space.runtime_status === "running"} onClick={() => void controlRuntime(space, "start")} className="ui-link">启动</button><button type="button" disabled={space.runtime_status !== "running"} onClick={() => void controlRuntime(space, "stop")} className="ui-link">停止</button><button type="button" disabled={space.id === user?.id} onClick={() => void updateMember(space, { disabled: space.status !== "disabled" })} className="ui-link">{space.status === "disabled" ? "恢复 Agent" : "禁止 Agent"}</button></div></td></tr>)}</tbody></table>{!agentSpaces.length && <p className="py-6 text-center text-sm text-ink-muted">暂无 AI Space，成员首次进入后会自动创建。</p>}</div>
        </div>
        <div className="ui-card lg:col-span-2"><div className="ui-card-header"><div className="flex items-center gap-2.5"><FileText className="h-4 w-4 text-ink-muted" /><h3 className="type-h3 text-ink">公共知识库</h3></div><span className="ui-tag">团队只读 · Admin 管理</span></div><div className="mb-4 flex flex-wrap gap-2"><input value={knowledgeQuery} onChange={event => setKnowledgeQuery(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder="搜索文件" /><button type="button" onClick={() => void fetchKnowledge()} className="ui-button-secondary">搜索</button><input value={knowledgeCategory} onChange={event => setKnowledgeCategory(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder="目录（可选）" /><label className="ui-button-primary cursor-pointer">上传文件<input type="file" className="hidden" onChange={event => void uploadKnowledge(event.target.files?.[0])} /></label></div><div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-ink-muted"><tr><th className="px-3 py-2">文件</th><th className="px-3 py-2">更新时间</th><th className="px-3 py-2">大小</th><th className="px-3 py-2">操作</th></tr></thead><tbody>{knowledgeFiles.map(file => <tr key={file.path} className="border-t border-grid/60"><td className="px-3 py-3 text-ink">{file.path}{file.managed && <span className="ml-2 ui-tag">系统同步</span>}</td><td className="px-3 py-3 text-ink-secondary">{new Date(file.updated_at).toLocaleString("zh-CN")}</td><td className="px-3 py-3 text-ink-secondary">{(file.size / 1024).toFixed(1)} KB</td><td className="px-3 py-3">{file.managed ? <span className="text-ink-muted">受保护</span> : <button type="button" onClick={() => void deleteKnowledge(file.path)} className="ui-link">删除</button>}</td></tr>)}</tbody></table></div></div>
        <div className="ui-card lg:col-span-2"><div className="ui-card-header"><h3 className="type-h3 text-ink">Artifact 知识审核</h3><span className="ui-tag">{artifactRequests.length} 待审核</span></div><div className="space-y-2">{artifactRequests.map(item => <div key={item.id} className="flex items-center justify-between rounded-lg bg-surface-subtle p-3 text-sm"><div><p className="font-semibold text-ink">{item.title}</p><p className="text-xs text-ink-muted">{item.type} · {new Date(item.created_at).toLocaleString("zh-CN")}</p></div><button type="button" onClick={() => void publishArtifact(item.id)} className="ui-button-primary px-3 py-1.5 text-xs">确认发布</button></div>)}{!artifactRequests.length && <p className="text-sm text-ink-muted">暂无待审核成果。</p>}</div></div>
        </>}
      </div>
      }

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
      {!adminOnly && <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="ui-button-primary px-6"
        >
          {saved ? <><RefreshCw className="h-4 w-4" /> 已保存</> : <><Save className="h-4 w-4" /> 保存设置</>}
        </button>
      </div>
      }
    </div>
  );
}
