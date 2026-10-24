"use client";

import { SectionHeader } from "@/components/section-header";
import { AgentLaunches } from "@/components/agent-launches";
import { usePreferences } from "@/lib/preferences";
import { DailyBoardInsight } from "@/components/daily-board-insight";
import { Sparkles } from "lucide-react";

export default function AppLaunchesPage() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";

  return (
    <div className="page-stack intel-subpage">
      <SectionHeader
        compact
        icon={<Sparkles className="h-5 w-5" />}
        title={en ? "AI Applications" : "AI 应用"}
      />
      <DailyBoardInsight board="apps" />
      <AgentLaunches />
    </div>
  );
}
