"use client";

import { User } from "lucide-react";
import Link from "next/link";
import { usePreferences } from "@/lib/preferences";

interface ProfileCardProps {
  user: { email?: string; user_metadata?: { name?: string } } | null;
  profileName: string;
  setProfileName: (value: string) => void;
  isAdmin: boolean;
}

export function ProfileCard({ user, profileName, setProfileName, isAdmin }: ProfileCardProps) {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  return (
    <div className="ui-card">
      <div className="ui-card-header">
        <User className="h-4 w-4 text-ink-muted" />
        <h3 className="type-h3 text-ink">{en ? "Profile" : "用户信息"}</h3>
      </div>
      <div className="space-y-3.5">
        <div>
          <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">{en ? "Name" : "用户名"}</label>
          <input type="text" value={profileName} onChange={event => setProfileName(event.target.value)} className="ui-input w-full px-3.5 py-2 text-sm" />
        </div>
        <div>
          <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">{en ? "Email" : "邮箱"}</label>
          <input type="email" value={user?.email || ""} disabled className="ui-input w-full bg-surface-subtle px-3.5 py-2 text-[13px]" />
        </div>
        <div>
          <label className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">{en ? "Plan" : "套餐"}</label>
          <div className="px-3.5 py-2 rounded-lg border border-grid bg-surface-subtle text-[13px] font-semibold text-ink flex items-center gap-2">
            InsightPro
            <span className="ui-tag">{isAdmin ? "Admin" : "User"}</span>
          </div>
        </div>
      </div>
      <div className="mt-4 border-t border-grid pt-3">
        <Link href="/auth/forgot-password" className="ui-link text-sm">{en ? "Forgot or reset password" : "忘记密码或重置密码"}</Link>
      </div>
    </div>
  );
}
