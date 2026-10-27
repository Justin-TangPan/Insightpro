"use client";

import { Users } from "lucide-react";
import { useState, useEffect } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import type { AccountUser } from "./types";

interface UserManagementCardProps {
  memberStatus: string;
  onStatusChange: (status: string) => void;
  onMemberUpdated: () => void;
  refreshVersion?: number;
}

export function UserManagementCard({ memberStatus, onStatusChange, onMemberUpdated, refreshVersion }: UserManagementCardProps) {
  const { preferences } = usePreferences();
  const t = (zh: string, en: string) => preferences.language === "en" ? en : zh;
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";

  const [users, setUsers] = useState<AccountUser[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");

  const fetchUsers = () => authenticatedFetch(`${API}/api/auth/users`)
    .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
    .then(data => setUsers(data.users || []))
    .catch(() => setUsers([]));

  const inviteMember = async () => {
    onStatusChange("");
    const response = await authenticatedFetch(`${API}/api/auth/users/invite`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: inviteEmail, name: inviteName, role: "admin" }) });
    const data = await response.json();
    if (!response.ok) return onStatusChange(data.detail || t("邀请发送失败", "Could not send invitation"));
    setInviteEmail(""); setInviteName(""); onStatusChange(t("管理员邀请已发送", "Administrator invitation sent")); void fetchUsers();
  };

  const updateMember = async (account: AccountUser, changes: { role?: "user" | "admin"; disabled?: boolean }) => {
    onStatusChange("");
    const response = await authenticatedFetch(`${API}/api/auth/users/${account.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(changes) });
    const data = await response.json();
    if (!response.ok) return onStatusChange(data.detail || t("成员更新失败", "Could not update member"));
    setUsers(items => items.map(item => item.id === account.id ? data.user : item));
    onMemberUpdated();
  };

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    void fetchUsers();
  }, [authLoading, isAdmin, refreshVersion]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="ui-card lg:col-span-2">
      <div className="ui-card-header">
        <div className="flex items-center gap-2.5"><Users className="h-4 w-4 text-ink-muted" /><h3 className="type-h3 text-ink">{t("用户系统", "User management")}</h3></div>
        <span className="ui-tag">{users.length} {t("位用户", "users")}</span>
      </div>
      <div className="mb-4 grid gap-2 rounded-xl bg-surface-subtle p-4 sm:grid-cols-[minmax(0,1fr)_9rem_auto]">
        <input type="email" value={inviteEmail} onChange={event => setInviteEmail(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder={t("成员邮箱", "Member email")} />
        <input type="text" value={inviteName} onChange={event => setInviteName(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder={t("姓名（可选）", "Name (optional)")} />
        <button type="button" onClick={() => void inviteMember()} disabled={!inviteEmail} className="ui-button-primary">{t("邀请管理员", "Invite administrator")}</button>
        {memberStatus && <p role="status" className="sm:col-span-4 text-xs text-ink-muted">{memberStatus}</p>}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-ink-muted"><tr><th className="px-3 py-2 font-semibold">{t("用户", "User")}</th><th className="px-3 py-2 font-semibold">{t("角色", "Role")}</th><th className="px-3 py-2 font-semibold">{t("状态", "Status")}</th><th className="px-3 py-2 font-semibold">{t("AI 空间", "AI space")}</th><th className="px-3 py-2 font-semibold">{t("操作", "Actions")}</th></tr></thead>
          <tbody>{users.map(account => <tr key={account.id} className="border-t border-grid/60"><td className="px-3 py-3"><p className="font-medium text-ink">{account.name || account.email?.split("@")[0]}</p><p className="text-ink-muted">{account.email}</p></td><td className="px-3 py-3">{account.role === "admin" ? "Admin" : t("普通用户", "User")}</td><td className="px-3 py-3"><span className={`ui-tag ${account.status === "disabled" ? "ui-tag-warning" : ""}`}>{account.status === "disabled" ? t("已禁用", "Disabled") : t("正常", "Active")}</span></td><td className="px-3 py-3 text-ink-secondary">{account.agent_space_status}</td><td className="px-3 py-3"><div className="flex gap-2"><button type="button" disabled={account.id === user?.id || account.role !== "admin"} onClick={() => void updateMember(account, { disabled: account.status !== "disabled" })} className="ui-link">{account.status === "disabled" ? t("恢复", "Restore") : t("禁用", "Disable")}</button></div></td></tr>)}</tbody>
        </table>
        {!users.length && <p className="py-8 text-center text-sm text-ink-muted">{t("暂无用户数据", "No users found")}</p>}
      </div>
    </div>
  );
}
