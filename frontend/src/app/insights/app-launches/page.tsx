"use client";

import { SectionHeader } from "@/components/section-header";
import { AgentLaunches } from "@/components/agent-launches";
import { usePreferences } from "@/lib/preferences";

export default function AppLaunchesPage() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";

  return (
    <div className="page-stack">
      <SectionHeader
        badge="AI Applications"
        title={en ? "AI Applications" : "AI 应用"}
        subtitle={en ? "Official AI application launches across major vendors, with source-grounded analysis." : "各大厂商官方 AI 应用发布与分析，分析以原文为依据。"}
        image="https://images.unsplash.com/photo-1618401471353-b98afee0b2eb?w=1200&q=80"
      />
      <AgentLaunches />
    </div>
  );
}