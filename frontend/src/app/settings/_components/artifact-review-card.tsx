"use client";

import { useState, useEffect } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import type { ArtifactRequest } from "./types";

interface ArtifactReviewCardProps {
  onStatusChange: (status: string) => void;
  onArtifactPublished?: () => void;
}

export function ArtifactReviewCard({ onStatusChange, onArtifactPublished }: ArtifactReviewCardProps) {
  const { preferences } = usePreferences();
  const t = (zh: string, en: string) => preferences.language === "en" ? en : zh;
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";

  const [artifactRequests, setArtifactRequests] = useState<ArtifactRequest[]>([]);

  const fetchArtifactRequests = () => authenticatedFetch(`${API}/api/agent/admin/artifacts/requests`)
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => setArtifactRequests(data.items || [])).catch(() => setArtifactRequests([]));

  const publishArtifact = async (id: string) => {
    const response = await authenticatedFetch(`${API}/api/agent/admin/artifacts/${id}/publish`, { method: "POST" });
    onStatusChange(response.ok ? t("Artifact 已沉淀到公共知识库", "Artifact published to public knowledge") : t("Artifact 发布失败", "Could not publish artifact")); if (response.ok) { void fetchArtifactRequests(); onArtifactPublished?.(); }
  };

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    void fetchArtifactRequests();
  }, [authLoading, isAdmin]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="ui-card lg:col-span-2"><div className="ui-card-header"><h3 className="type-h3 text-ink">{t("Artifact 知识审核", "Artifact knowledge review")}</h3><span className="ui-tag">{artifactRequests.length} {t("待审核", "pending")}</span></div><div className="space-y-2">{artifactRequests.map(item => <div key={item.id} className="flex items-center justify-between rounded-lg bg-surface-subtle p-3 text-sm"><div><p className="font-semibold text-ink">{item.title}</p><p className="text-xs text-ink-muted">{item.type} · {new Date(item.created_at).toLocaleString(preferences.language === "en" ? "en-US" : "zh-CN")}</p></div><button type="button" onClick={() => void publishArtifact(item.id)} className="ui-button-primary px-3 py-1.5 text-xs">{t("确认发布", "Publish")}</button></div>)}{!artifactRequests.length && <p className="text-sm text-ink-muted">{t("暂无待审核成果。", "No artifacts pending review.")}</p>}</div></div>
  );
}
