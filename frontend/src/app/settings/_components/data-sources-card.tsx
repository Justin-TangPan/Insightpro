"use client";

import { Database } from "lucide-react";
import { useState, useEffect } from "react";
import { API } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";

export function DataSourcesCard() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";
  const [checks, setChecks] = useState<Record<string, boolean> | null>(null);

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    fetch(`${API}/api/system/health/ready`)
      .then((res) => res.json())
      .then((report) => setChecks(report.checks || {}))
      .catch(() => setChecks({}));
  }, [authLoading, isAdmin]);

  const dataSources = [
    ["GitHub Trending", checks?.github_trending_nonempty],
    [en ? "Alibaba Cloud solutions" : "阿里云方案", checks?.aliyun_solutions_nonempty],
    [en ? "Huawei Cloud solutions" : "华为云方案", checks?.huawei_solutions_nonempty],
    ["Supabase", checks?.database],
  ].map(([name, ok]) => ({ name, ok: ok === true, status: ok === true ? (en ? "Healthy" : "正常") : (en ? "Unavailable" : "异常") }));

  return (
    <div className="ui-card">
      <div className="ui-card-header">
        <Database className="h-4 w-4 text-ink-muted" />
        <h3 className="type-h3 text-ink">{en ? "Data source health" : "数据源状态"}</h3>
      </div>
      <div className="space-y-0.5">
        {!checks ? <div className="h-40 animate-shimmer rounded-xl" /> : dataSources.map((src) => (
          <div key={String(src.name)} className="flex items-center justify-between rounded-lg px-3 py-2.5 odd:bg-surface-subtle/60">
            <span className="text-sm font-medium text-ink">{src.name}</span>
            <span className={`ui-tag ${src.ok ? "ui-tag-success" : "ui-tag-danger"}`}>
              {src.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
