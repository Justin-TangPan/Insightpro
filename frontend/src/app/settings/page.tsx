"use client";

import { SectionHeader } from "@/components/section-header";
import { useState, useEffect } from "react";
import { Save, RefreshCw, Bell, Database, Shield, User, Mail, Send, Plus, Trash2, CheckCircle2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Subscriber {
  id: number;
  email: string;
  name: string;
  active: number;
}

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);
  const [toggles, setToggles] = useState([true, true, true, false]);
  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [emailStatus, setEmailStatus] = useState("");
  const [testing, setTesting] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleToggle = (index: number) => {
    setToggles((prev) => prev.map((v, i) => (i === index ? !v : v)));
  };

  // Fetch subscribers
  const fetchSubscribers = async () => {
    try {
      const res = await fetch(`${API}/api/email/subscribers`);
      const data = await res.json();
      setSubscribers(data.subscribers || []);
    } catch (err) {
      console.error("Failed to fetch subscribers:", err);
    }
  };

  useEffect(() => {
    fetchSubscribers();
  }, []);

  // Add subscriber
  const handleSubscribe = async () => {
    if (!newEmail) return;
    try {
      const res = await fetch(`${API}/api/email/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: newEmail, name: newName }),
      });
      const data = await res.json();
      setEmailStatus(data.message);
      setNewEmail("");
      setNewName("");
      fetchSubscribers();
      setTimeout(() => setEmailStatus(""), 3000);
    } catch (err) {
      setEmailStatus("订阅失败");
    }
  };

  // Remove subscriber
  const handleRemove = async (email: string) => {
    try {
      await fetch(`${API}/api/email/subscribers/${encodeURIComponent(email)}`, { method: "DELETE" });
      fetchSubscribers();
    } catch (err) {
      console.error("Failed to remove subscriber:", err);
    }
  };

  // Test email
  const handleTestEmail = async () => {
    setTesting(true);
    try {
      const res = await fetch(`${API}/api/email/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "1315304560@qq.com" }),
      });
      const data = await res.json();
      setEmailStatus(data.message || "测试邮件已发送");
      setTimeout(() => setEmailStatus(""), 5000);
    } catch (err) {
      setEmailStatus("发送失败，请检查 SMTP 配置");
    } finally {
      setTesting(false);
    }
  };

  const notifications = [
    { label: "每日洞察日报", desc: "每天 09:00 推送今日商业洞察摘要" },
    { label: "友商动态预警", desc: "友商有重大动态时实时推送" },
    { label: "政策法规更新", desc: "等保、信创等政策变化时推送" },
    { label: "系统异常告警", desc: "API 或数据源异常时推送" },
  ];

  const dataSources = [
    { name: "GitHub Trending", status: "已连接", ok: true },
    { name: "百度热搜", status: "已连接", ok: true },
    { name: "DeepSeek AI", status: "已连接", ok: true },
    { name: "Supabase", status: "未配置", ok: false },
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
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">用户名</label>
              <input type="text" defaultValue="Justin Tang" className="w-full px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[13px] text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors" />
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
                  <p className="text-[13px] font-medium text-ink">{item.label}</p>
                  <p className="text-[11px] text-ink-muted mt-0.5">{item.desc}</p>
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
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <Mail className="h-4 w-4 text-ink-muted" />
              <h3 className="font-semibold text-sm text-ink">邮件订阅管理</h3>
              <span className="text-[10px] font-medium text-ink-muted">每天 09:05 自动发送</span>
            </div>
            <button
              onClick={handleTestEmail}
              disabled={testing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-50 border border-slate-200 text-ink-secondary hover:bg-slate-100 transition-colors disabled:opacity-50"
            >
              <Send className={`h-3 w-3 ${testing ? "animate-pulse" : ""}`} />
              {testing ? "发送中..." : "测试发送"}
            </button>
          </div>

          {/* Add subscriber */}
          <div className="flex gap-2 mb-4">
            <input
              type="email"
              placeholder="收件人邮箱"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="flex-1 px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[13px] text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors"
            />
            <input
              type="text"
              placeholder="姓名（可选）"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-32 px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[13px] text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors"
            />
            <button
              onClick={handleSubscribe}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              添加
            </button>
          </div>

          {emailStatus && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-200 mb-4">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              <span className="text-xs text-emerald-700">{emailStatus}</span>
            </div>
          )}

          {/* Subscriber list */}
          <div className="space-y-1">
            {subscribers.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-sm text-ink-muted">暂无订阅者</p>
                <p className="text-[11px] text-ink-muted mt-1">默认发送至 tangpan10@huawei.com</p>
              </div>
            ) : (
              subscribers.map((sub) => (
                <div key={sub.id} className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="h-7 w-7 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-ink-muted">
                      {(sub.name || sub.email)[0].toUpperCase()}
                    </div>
                    <div>
                      <p className="text-[13px] font-medium text-ink">{sub.email}</p>
                      {sub.name && <p className="text-[10px] text-ink-muted">{sub.name}</p>}
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemove(sub.email)}
                    className="p-1.5 rounded-md hover:bg-rose-50 text-ink-muted hover:text-rose-500 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
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
                <span className="text-[13px] font-medium text-ink">{src.name}</span>
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
              <input type="password" defaultValue="sk-xxxx" className="w-full px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[13px] font-mono text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors" />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">数据库连接</label>
              <input type="password" defaultValue="postgresql://..." className="w-full px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[13px] font-mono text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors" />
            </div>
          </div>
        </div>
      </div>

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
