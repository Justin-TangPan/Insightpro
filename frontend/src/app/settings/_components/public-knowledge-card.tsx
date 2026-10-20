"use client";

import { FileText, RefreshCw } from "lucide-react";
import { useState, useEffect } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import { ConfirmDialog } from "@/components/ui";

interface PublicKnowledgeCardProps {
  onStatusChange: (status: string) => void;
  refreshVersion?: number;
}

export function PublicKnowledgeCard({ onStatusChange, refreshVersion }: PublicKnowledgeCardProps) {
  const { preferences } = usePreferences();
  const t = (zh: string, en: string) => preferences.language === "en" ? en : zh;
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";

  const [knowledgeFiles, setKnowledgeFiles] = useState<{ path: string; size: number; updated_at: string; managed: boolean }[]>([]);
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeCategory, setKnowledgeCategory] = useState("");
  const [knowledgeOverview, setKnowledgeOverview] = useState({ documents: 0, chunks: 0, sources: [] as { source_type: string; documents: number }[] });
  const [knowledgeIndexing, setKnowledgeIndexing] = useState(false);
  const [pendingKnowledgeDelete, setPendingKnowledgeDelete] = useState("");

  const fetchKnowledge = (query = knowledgeQuery) => authenticatedFetch(`${API}/api/auth/public-knowledge?query=${encodeURIComponent(query)}`)
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => setKnowledgeFiles(data.files || []))
    .catch(() => setKnowledgeFiles([]));
  const fetchKnowledgeOverview = () => authenticatedFetch(`${API}/api/agent/knowledge/overview`)
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => setKnowledgeOverview(data)).catch(() => undefined);

  const uploadKnowledge = async (file?: File) => {
    if (!file) return;
    const data = new FormData(); data.append("file", file); data.append("category", knowledgeCategory);
    const response = await authenticatedFetch(`${API}/api/auth/public-knowledge`, { method: "POST", body: data });
    onStatusChange(response.ok ? t("公共知识已上传并建立索引", "Public knowledge uploaded and indexed") : t("公共知识上传失败", "Could not upload public knowledge")); if (response.ok) { void fetchKnowledge(); void fetchKnowledgeOverview(); }
  };

  const reindexKnowledge = async () => {
    setKnowledgeIndexing(true); onStatusChange("");
    const response = await authenticatedFetch(`${API}/api/agent/admin/knowledge/reindex`, { method: "POST" });
    const data = await response.json().catch(() => ({}));
    onStatusChange(response.ok ? t(`知识索引已同步，本次更新 ${data.indexed_chunks || 0} 个片段`, `Knowledge index synced; ${data.indexed_chunks || 0} chunks updated`) : t("知识索引同步失败", "Could not sync knowledge index"));
    setKnowledgeIndexing(false); if (response.ok) void fetchKnowledgeOverview();
  };

  const deleteKnowledge = async (path: string) => {
    const response = await authenticatedFetch(`${API}/api/auth/public-knowledge?path=${encodeURIComponent(path)}`, { method: "DELETE" });
    onStatusChange(response.ok ? t("公共知识已删除", "Public knowledge deleted") : t("该文件受保护或删除失败", "File is protected or could not be deleted"));
    if (!response.ok) throw new Error(t("该文件受保护或删除失败", "File is protected or could not be deleted"));
    void fetchKnowledge();
  };

  useEffect(() => {
    if (authLoading || !isAdmin) return;
    void fetchKnowledge("");
    void fetchKnowledgeOverview();
  }, [authLoading, isAdmin, refreshVersion]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <div className="ui-card lg:col-span-2"><div className="ui-card-header"><div className="flex items-center gap-2.5"><FileText className="h-4 w-4 text-ink-muted" /><div><h3 className="type-h3 text-ink">{t("公共知识库与索引", "Public knowledge and index")}</h3><p className="mt-1 text-xs text-ink-muted">{t("上传文本会立即向量化；系统数据可手动增量同步。", "Uploaded text is indexed immediately. System data can be synced manually.")}</p></div></div><button type="button" onClick={() => void reindexKnowledge()} disabled={knowledgeIndexing} className="ui-button-secondary"><RefreshCw className={`h-3.5 w-3.5 ${knowledgeIndexing ? "animate-spin" : ""}`} />{knowledgeIndexing ? t("同步中", "Syncing") : t("同步索引", "Sync index")}</button></div><div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4"><div className="rounded-xl bg-surface-subtle p-3"><p className="text-xs text-ink-muted">{t("知识对象", "Documents")}</p><p className="mt-1 text-xl font-semibold text-ink">{knowledgeOverview.documents}</p></div><div className="rounded-xl bg-surface-subtle p-3"><p className="text-xs text-ink-muted">{t("向量片段", "Vector chunks")}</p><p className="mt-1 text-xl font-semibold text-ink">{knowledgeOverview.chunks}</p></div>{knowledgeOverview.sources.slice(0, 2).map(source => <div key={source.source_type} className="rounded-xl bg-surface-subtle p-3"><p className="truncate text-xs text-ink-muted">{source.source_type}</p><p className="mt-1 text-xl font-semibold text-ink">{source.documents}</p></div>)}</div><div className="mb-4 flex flex-wrap gap-2"><input value={knowledgeQuery} onChange={event => setKnowledgeQuery(event.target.value)} spellCheck={false} className="ui-input px-3 py-2 text-sm" placeholder={t("搜索文件", "Search files")} /><button type="button" onClick={() => void fetchKnowledge()} className="ui-button-secondary">{t("搜索", "Search")}</button><input value={knowledgeCategory} onChange={event => setKnowledgeCategory(event.target.value)} className="ui-input px-3 py-2 text-sm" placeholder={t("目录（可选）", "Category (optional)")} /><label className="ui-button-primary cursor-pointer">{t("上传 UTF-8 文本", "Upload UTF-8 text")}<input type="file" accept=".md,.txt,.csv,.json,.yaml,.yml" className="hidden" onChange={event => void uploadKnowledge(event.target.files?.[0])} /></label></div><div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-ink-muted"><tr><th className="px-3 py-2">{t("文件", "File")}</th><th className="px-3 py-2">{t("更新时间", "Updated")}</th><th className="px-3 py-2">{t("大小", "Size")}</th><th className="px-3 py-2">{t("操作", "Actions")}</th></tr></thead><tbody>{knowledgeFiles.map(file => <tr key={file.path} className="border-t border-grid/60"><td className="px-3 py-3 text-ink">{file.path}{file.managed && <span className="ml-2 ui-tag">{t("系统同步", "System synced")}</span>}</td><td className="px-3 py-3 text-ink-secondary">{new Date(file.updated_at).toLocaleString(preferences.language === "en" ? "en-US" : "zh-CN")}</td><td className="px-3 py-3 text-ink-secondary">{(file.size / 1024).toFixed(1)} KB</td><td className="px-3 py-3">{file.managed ? <span className="text-ink-muted">{t("受保护", "Protected")}</span> : <button type="button" onClick={() => setPendingKnowledgeDelete(file.path)} className="ui-link">{t("删除", "Delete")}</button>}</td></tr>)}</tbody></table>{!knowledgeFiles.length && <p className="py-8 text-center text-sm text-ink-muted">{t("暂无人工上传文件，系统知识索引仍正常工作。", "No uploaded files. The system knowledge index remains available.")}</p>}</div></div>

      <ConfirmDialog open={!!pendingKnowledgeDelete} onOpenChange={(open) => { if (!open) setPendingKnowledgeDelete(""); }} title={t("删除公共知识文件？", "Delete public knowledge file?")} description={pendingKnowledgeDelete ? t(`「${pendingKnowledgeDelete}」将被永久删除。`, `${pendingKnowledgeDelete} will be permanently deleted.`) : undefined} confirmLabel={t("删除", "Delete")} danger onConfirm={() => deleteKnowledge(pendingKnowledgeDelete)} />
    </>
  );
}
