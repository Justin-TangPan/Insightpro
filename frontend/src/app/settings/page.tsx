"use client";

import { SectionHeader } from "@/components/section-header";
import { useState, useEffect } from "react";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import { Save, RefreshCw } from "lucide-react";
import { ProfileCard } from "./_components/profile-card";
import { NotificationSettingsCard } from "./_components/notification-settings-card";
import { AppearancePreferencesCard } from "./_components/appearance-preferences-card";
import { EmailSubscriptionManager } from "./_components/email-subscription-manager";
import { AiRuntimeConfigCard } from "./_components/ai-runtime-config-card";
import { DataSourcesCard } from "./_components/data-sources-card";
import { UserManagementCard } from "./_components/user-management-card";
import { AiSpaceManagerCard } from "./_components/ai-space-manager-card";
import { PublicKnowledgeCard } from "./_components/public-knowledge-card";
import { ArtifactReviewCard } from "./_components/artifact-review-card";

type AdminSection = "runtime" | "access" | "knowledge";

export default function SettingsPage({ adminOnly = false, adminSection = "runtime" }: { adminOnly?: boolean; adminSection?: AdminSection }) {
  const { user, loading: authLoading, updateProfile } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";
  const { preferences, updatePreferences } = usePreferences();
  const [profileName, setProfileName] = useState("");
  const [saved, setSaved] = useState(false);
  const [memberStatus, setMemberStatus] = useState("");
  const [memberUpdateCount, setMemberUpdateCount] = useState(0);
  const [knowledgeRefreshCount, setKnowledgeRefreshCount] = useState(0);

  const handleSave = async () => {
    if (user && profileName !== (user.user_metadata?.name || "")) await updateProfile(profileName);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleMemberUpdated = () => setMemberUpdateCount(c => c + 1);
  const handleKnowledgeRefresh = () => setKnowledgeRefreshCount(c => c + 1);
  const adminCopy = {
    runtime: ["运行与数据", "管理模型连接、数据源与邮件订阅", "Runtime & data", "Manage models, data sources and email subscriptions"],
    access: ["用户与权限", "管理成员角色、AI Space 与运行环境", "Users & access", "Manage member roles, AI Spaces and runtimes"],
    knowledge: ["知识库与产物", "管理公共知识、索引与产物审核", "Knowledge & artifacts", "Manage public knowledge, indexes and artifact review"],
  }[adminSection];

  useEffect(() => {
    if (authLoading) return;
    void Promise.resolve().then(() => setProfileName(user?.user_metadata?.name || ""));
  }, [authLoading, user]);

  return (
    <div className="page-stack">
      <SectionHeader
        badge={adminOnly ? "Admin" : "Settings"}
        title={adminOnly ? adminCopy[preferences.language === "en" ? 2 : 0] : (preferences.language === "en" ? "System Settings" : "系统设置")}
        subtitle={adminOnly ? adminCopy[preferences.language === "en" ? 3 : 1] : (preferences.language === "en" ? "Manage your account, appearance and preferences" : "管理账号、外观与使用偏好")}
      />

      {adminOnly && !isAdmin ? <div className="ui-card py-12 text-center text-sm text-ink-muted">{preferences.language === "en" ? "Administrator access required." : "需要管理员权限。"}</div> : <>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {!adminOnly && <>
          <ProfileCard user={user} profileName={profileName} setProfileName={setProfileName} isAdmin={isAdmin} />
          <NotificationSettingsCard />
          <AppearancePreferencesCard preferences={preferences} updatePreferences={updatePreferences} />
        </>}

        {adminOnly && isAdmin && <>
          {adminSection === "runtime" && <>
            <AiRuntimeConfigCard />
            <DataSourcesCard />
            <EmailSubscriptionManager />
          </>}
          {adminSection === "access" && <>
            <UserManagementCard memberStatus={memberStatus} onStatusChange={setMemberStatus} onMemberUpdated={handleMemberUpdated} refreshVersion={memberUpdateCount} />
            <AiSpaceManagerCard onStatusChange={setMemberStatus} onMemberUpdated={handleMemberUpdated} refreshVersion={memberUpdateCount} />
          </>}
          {adminSection === "knowledge" && <>
            <PublicKnowledgeCard onStatusChange={setMemberStatus} refreshVersion={knowledgeRefreshCount} />
            <ArtifactReviewCard onStatusChange={setMemberStatus} onArtifactPublished={handleKnowledgeRefresh} />
          </>}
        </>}
        </div>
      </>
      }

      {!adminOnly && <div className="flex justify-end">
        <button onClick={handleSave} className="ui-button-primary px-6">
          {saved ? <><RefreshCw className="h-4 w-4" /> {preferences.language === "en" ? "Saved" : "已保存"}</> : <><Save className="h-4 w-4" /> {preferences.language === "en" ? "Save settings" : "保存设置"}</>}
        </button>
      </div>}
    </div>
  );
}
