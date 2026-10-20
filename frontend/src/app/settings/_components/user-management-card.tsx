"use client";

import { Users, Bot } from "lucide-react";
import Link from "next/link";
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
  const [inviteRole, setInviteRole] = useState<"user" | "admin">("user");
  const [testUsername, setTestUsername] = useState("");
  const [testPassword, setTestPassword] = useState("");
  const [testName, setTestName] = useState("");

  const fetchUsers = () => authenticatedFetch(`${API}/api/auth/users`)
    .then(response => response.ok ? response.json() : Promise.reject(new Error(String(response.status))))
    .then(data => setUsers(data.users || []))
    .catch(() => setUsers([]));

  const inviteMember = async () => {
    onStatusChange("");
    const response = await authenticatedFetch(`${API}/api/auth/users/invite`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: inviteEmail, name: inviteName, role: inviteRole }) });
    const data = await response.json();
    if (!response.ok) return onStatusChange(data.detail || t("邀请发送失败", "Could not send invitation"));
    setInviteEmail(""); setInviteName(""); setInviteRole("user"); onStatusChange(t("邀请已发送", "Invitation sent")); void fetchUsers();
  };

  const createTestMember = async () => {
    onStatusChange("");
    const response = await authenticatedFetch(`${API}/api/auth/users/test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: testUsername, password: testPassword, name: testName, role: "user" }) });
    const data = await response.json();
    if (!response.ok) return onStatusChange(data.detail || t("测试账号创建失败", "Could not create test account"));
    setTestUsername(""); setTestPassword(""); setTestName(""); onStatusChange(t("测试账号已创建", "Test account created")); void fetchUsers();
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
      <div className="mb-4 grid gap-2 rounded-xl bg-surface-subtle p-4 sm:grid-cols-[minmax(0,1fr)_9rem_7rem_auto]">
        <input type="email" value={inviteEmail} onChange={event => setInviteEmail(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder={t("成员邮箱", "Member email")} />
        <input type="text" value={inviteName} onChange={event => setInviteName(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder={t("姓名（可选）", "Name (optional)")} />
        <select value={inviteRole} onChange={event => setInviteRole(event.target.value as "user" | "admin")} className="ui-input px-3 py-2 text-sm"><option value="user">{t("普通用户", "User")}</option><option value="admin">Admin</option></select>
        <button type="button" onClick={() => void inviteMember()} disabled={!inviteEmail} className="ui-button-primary">{t("邀请成员", "Invite member")}</button>
        {memberStatus && <p role="status" className="sm:col-span-4 text-xs text-ink-muted">{memberStatus}</p>}
      </div>
      <div className="mb-4 grid gap-2 rounded-xl border border-grid bg-surface-subtle p-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_9rem_auto]">
        <input value={testUsername} onChange={event => setTestUsername(event.target.value)} autoComplete="off" className="ui-input px-3 py-2 text-sm" placeholder={t("测试用户名，如 demo01", "Test username, e.g. demo01")} />
        <input type="password" value={testPassword} onChange={event => setTestPassword(event.target.value)} autoComplete="new-password" className="ui-input px-3 py-2 text-sm" placeholder={t("初始密码（至少 8 位）", "Initial password (8+ characters)")} />
        <input value={testName} onChange={event => setTestName(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder={t("显示名称", "Display name")} />
        <button type="button" onClick={() => void createTestMember()} disabled={!testUsername || testPassword.length < 8} className="ui-button-secondary">{t("创建测试账号", "Create test account")}</button>
        <p className="sm:col-span-4 text-xs text-ink-muted">{t("测试账号不发送邮件；创建后用用户名和初始密码直接登录。", "Test accounts do not receive email. Sign in with the username and initial password.")}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-ink-muted"><tr><th className="px-3 py-2 font-semibold">{t("用户", "User")}</th><th className="px-3 py-2 font-semibold">{t("角色", "Role")}</th><th className="px-3 py-2 font-semibold">{t("状态", "Status")}</th><th className="px-3 py-2 font-semibold">{t("AI 空间", "AI space")}</th><th className="px-3 py-2 font-semibold">{t("操作", "Actions")}</th></tr></thead>
          <tbody>{users.map(account => <tr key={account.id} className="border-t border-grid/60"><td className="px-3 py-3"><p className="font-medium text-ink">{account.name || account.email?.split("@")[0]}</p><p className="text-ink-muted">{account.email}</p></td><td className="px-3 py-3"><select value={account.role} disabled={account.id === user?.id} onChange={event => void updateMember(account, { role: event.target.value as "user" | "admin" })} className="ui-input px-2 py-1 text-xs"><option value="user">{t("普通用户", "User")}</option><option value="admin">Admin</option></select></td><td className="px-3 py-3"><span className={`ui-tag ${account.status === "disabled" ? "ui-tag-warning" : ""}`}>{account.status === "disabled" ? t("已禁用", "Disabled") : t("正常", "Active")}</span></td><td className="px-3 py-3 text-ink-secondary">{account.agent_space_status}</td><td className="px-3 py-3"><div className="flex gap-2"><Link href={`/insight-agent?target=${account.id}`} className="ui-link inline-flex items-center gap-1"><Bot className="h-3.5 w-3.5" />{t("管理", "Manage")}</Link><button type="button" disabled={account.id === user?.id} onClick={() => void updateMember(account, { disabled: account.status !== "disabled" })} className="ui-link">{account.status === "disabled" ? t("恢复", "Restore") : t("禁用", "Disable")}</button></div></td></tr>)}</tbody>
        </table>
        {!users.length && <p className="py-8 text-center text-sm text-ink-muted">{t("暂无用户数据", "No users found")}</p>}
      </div>
    </div>
  );
}
