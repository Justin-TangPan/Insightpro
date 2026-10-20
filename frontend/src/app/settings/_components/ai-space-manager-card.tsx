"use client";

import { Bot } from "lucide-react";
import Link from "next/link";
import { useState, useEffect } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import type { AccountUser, AgentSpace, AgentUsage } from "./types";

interface AiSpaceManagerCardProps {
  onStatusChange: (status: string) => void;
  onMemberUpdated: () => void;
  refreshVersion?: number;
}

export function AiSpaceManagerCard({ onStatusChange, onMemberUpdated, refreshVersion }: AiSpaceManagerCardProps) {
  const { preferences } = usePreferences();
  const t = (zh: string, en: string) => preferences.language === "en" ? en : zh;
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";

  const [agentSpaces, setAgentSpaces] = useState<AgentSpace[]>([]);
  const [agentSummary, setAgentSummary] = useState({ ai_space_users: 0, active_runtimes: 0, max_active_runtimes: 0, today: { date: "", requests: 0, input_tokens: 0, output_tokens: 0 } });
  const [agentUsage, setAgentUsage] = useState<AgentUsage[]>([]);

  const fetchAgentSpaces = () => authenticatedFetch(`${API}/api/auth/agent-spaces`)
    .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
    .then(data => { setAgentSpaces(data.spaces || []); setAgentUsage(data.usage || []); setAgentSummary(data); })
    .catch(() => { setAgentSpaces([]); setAgentUsage([]); setAgentSummary({ ai_space_users: 0, active_runtimes: 0, max_active_runtimes: 0, today: { date: "", requests: 0, input_tokens: 0, output_tokens: 0 } }); });

  const controlRuntime = async (space: AgentSpace, action: "start" | "stop") => {
    onStatusChange("");
    const response = await authenticatedFetch(`${API}/api/auth/agent-spaces/${space.id}/${action}`, { method: "POST" });
    if (!response.ok) return onStatusChange((await response.json()).detail || t("Runtime 操作失败", "Runtime action failed"));
    onStatusChange(action === "start" ? t("Runtime 已启动", "Runtime started") : t("Runtime 已停止", "Runtime stopped"));
    void fetchAgentSpaces();
  };

  const updateMember = async (account: AccountUser, changes: { role?: "user" | "admin"; disabled?: boolean }) => {
    onStatusChange("");
    const response = await authenticatedFetch(`${API}/api/auth/users/${account.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(changes) });
    const data = await response.json();
    if (!response.ok) return onStatusChange(data.detail || t("成员更新失败", "Could not update member"));
    void fetchAgentSpaces();
    onMemberUpdated();
  };

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    void fetchAgentSpaces();
  }, [authLoading, isAdmin, refreshVersion]); // eslint-disable-line react-hooks/exhaustive-deps

  const usageDays = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(); date.setUTCDate(date.getUTCDate() - (6 - index));
    return date.toISOString().slice(0, 10);
  });
  const dailyUsage = usageDays.map(date => ({ date, requests: agentUsage.reduce((sum, item) => sum + (item.days[date]?.requests || 0), 0) }));
  const usageRanking = [...agentUsage].sort((a, b) => (b.days[agentSummary.today.date]?.requests || 0) - (a.days[agentSummary.today.date]?.requests || 0)).slice(0, 3);

  return (
    <div className="ui-card lg:col-span-2">
      <div className="ui-card-header"><div className="flex items-center gap-2.5"><Bot className="h-4 w-4 text-ink-muted" /><h3 className="type-h3 text-ink">{t("AI Space 管理", "AI Space management")}</h3></div><span className="ui-tag">{agentSummary.active_runtimes} / {agentSummary.max_active_runtimes} Runtime</span></div>
      <div className="mb-4 grid grid-cols-3 gap-3 text-center text-xs"><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">{t("AI Space 用户", "AI Space users")}</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.ai_space_users}</p></div><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">{t("在线 Runtime", "Active runtimes")}</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.active_runtimes}</p></div><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">{t("最大并发", "Max concurrency")}</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.max_active_runtimes}</p></div></div>
      <div className="mb-4 grid grid-cols-3 gap-3 text-center text-xs"><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">{t("今日 Agent 用户", "Agent users today")}</p><p className="mt-1 text-lg font-semibold text-ink">{agentUsage.filter(item => (item.days[agentSummary.today.date]?.requests || 0) > 0).length}</p></div><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">{t("今日请求", "Requests today")}</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.today.requests}</p></div><div className="rounded-lg bg-surface-subtle p-3"><p className="text-ink-muted">{t("今日 Token", "Tokens today")}</p><p className="mt-1 text-lg font-semibold text-ink">{agentSummary.today.input_tokens + agentSummary.today.output_tokens}</p></div></div>
      <p className="mb-1 text-xs text-ink-muted">{t("近 7 天请求", "Requests, last 7 days")}: {dailyUsage.map(item => `${item.date.slice(5)} ${item.requests}`).join(" · ")}</p><p className="mb-3 text-xs text-ink-muted">{t("Token 仅在模型 Provider 返回 usage 时记录；未返回时只统计真实请求。用户排行", "Tokens are recorded when the provider returns usage. Top users")}: {usageRanking.map(item => `${agentSpaces.find(space => space.id === item.user_id)?.email || item.user_id.slice(0, 8)} ${(item.days[agentSummary.today.date]?.requests || 0)} ${t("次", "requests")}`).join(" · ") || t("暂无使用数据", "No usage data")}</p>
      <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-ink-muted"><tr><th className="px-3 py-2">{t("成员", "Member")}</th><th className="px-3 py-2">Runtime</th><th className="px-3 py-2">Workspace</th><th className="px-3 py-2">{t("最近使用", "Last used")}</th><th className="px-3 py-2">{t("占用", "Storage")}</th><th className="px-3 py-2">{t("操作", "Actions")}</th></tr></thead><tbody>{agentSpaces.map(space => <tr key={space.id} className="border-t border-grid/60"><td className="px-3 py-3"><p className="font-medium text-ink">{space.name || space.email.split("@")[0]}</p><p className="text-ink-muted">{space.status === "disabled" ? t("Agent 已禁用", "Agent disabled") : space.email}</p></td><td className="px-3 py-3"><span className={`ui-tag ${space.runtime_status === "running" ? "" : "ui-tag-warning"}`}>{space.runtime_status === "running" ? t("运行中", "Running") : t("已停止", "Stopped")}</span></td><td className="px-3 py-3 text-ink-secondary">{space.workspace_status === "ready" ? t("已创建", "Created") : t("未创建", "Not created")}</td><td className="px-3 py-3 text-ink-secondary">{space.last_used_at ? new Date(space.last_used_at).toLocaleString(preferences.language === "en" ? "en-US" : "zh-CN") : "—"}</td><td className="px-3 py-3 text-ink-secondary">{space.disk_bytes ? `${(space.disk_bytes / 1024 / 1024).toFixed(1)} MB` : "—"}</td><td className="px-3 py-3"><div className="flex gap-2"><Link href={`/insight-agent?target=${space.id}`} className="ui-link">{t("进入", "Open")}</Link><button type="button" disabled={space.status === "disabled" || space.runtime_status === "running"} onClick={() => void controlRuntime(space, "start")} className="ui-link">{t("启动", "Start")}</button><button type="button" disabled={space.runtime_status !== "running"} onClick={() => void controlRuntime(space, "stop")} className="ui-link">{t("停止", "Stop")}</button><button type="button" disabled={space.id === user?.id} onClick={() => void updateMember(space, { disabled: space.status !== "disabled" })} className="ui-link">{space.status === "disabled" ? t("恢复 Agent", "Restore Agent") : t("禁止 Agent", "Disable Agent")}</button></div></td></tr>)}</tbody></table>{!agentSpaces.length && <p className="py-6 text-center text-sm text-ink-muted">{t("暂无 AI Space，成员首次进入后会自动创建。", "No AI Spaces yet. One will be created when a member first opens the Agent.")}</p>}</div>
    </div>
  );
}
