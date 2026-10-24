"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Eye, EyeOff, KeyRound, Loader2, Pencil, PlugZap, Search } from "lucide-react";
import { AppDialog } from "@/components/ui";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";

type Config = { EMBEDDING_API_URL: string; EMBEDDING_MODEL: string; EMBEDDING_API_KEY: string };
type Status = { ok: boolean; text: string } | null;

export function EmbeddingConfigCard() {
  const { preferences } = usePreferences();
  const t = useCallback((zh: string, en: string) => preferences.language === "en" ? en : zh, [preferences.language]);
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";
  const [config, setConfig] = useState<Config>({ EMBEDDING_API_URL: "", EMBEDDING_MODEL: "", EMBEDDING_API_KEY: "" });
  const [draft, setDraft] = useState(config);
  const [dimensions, setDimensions] = useState(1024);
  const [configured, setConfigured] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [status, setStatus] = useState<Status>(null);

  const fetchConfig = useCallback(() => authenticatedFetch(`${API}/api/auth/admin/embedding-config`)
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => {
      const next = { EMBEDDING_API_URL: data.config?.EMBEDDING_API_URL || "", EMBEDDING_MODEL: data.config?.EMBEDDING_MODEL || "", EMBEDDING_API_KEY: "" };
      setConfig(next); setDraft(next); setDimensions(data.dimensions || 1024); setConfigured(Boolean(data.api_key_configured));
    })
    .catch(() => setStatus({ ok: false, text: t("无法读取向量模型配置", "Could not load embedding configuration") })), [t]);

  useEffect(() => { if (!authLoading && isAdmin) void fetchConfig(); }, [authLoading, isAdmin, fetchConfig]);

  const request = async (method: "POST" | "PATCH") => {
    const path = method === "POST" ? "/verify" : "";
    const response = await authenticatedFetch(`${API}/api/auth/admin/embedding-config${path}`, {
      method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || t("连接失败，请检查配置", "Connection failed. Check the configuration."));
    return data;
  };

  const testConnection = async () => {
    setTesting(true); setStatus(null);
    try {
      const result = await request("POST");
      setStatus({ ok: true, text: t(`连接成功 · ${result.dimensions} 维`, `Connected · ${result.dimensions} dimensions`) });
    } catch (error) { setStatus({ ok: false, text: error instanceof Error ? error.message : t("连接失败", "Connection failed") }); }
    finally { setTesting(false); }
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setSaving(true); setStatus(null);
    try {
      const result = await request("PATCH");
      const next = { EMBEDDING_API_URL: result.config.EMBEDDING_API_URL, EMBEDDING_MODEL: result.config.EMBEDDING_MODEL, EMBEDDING_API_KEY: "" };
      setConfig(next); setDraft(next); setConfigured(true); setDimensions(result.dimensions); setOpen(false);
      setStatus({ ok: true, text: t("向量模型配置已验证并保存", "Embedding configuration verified and saved") });
    } catch (error) { setStatus({ ok: false, text: error instanceof Error ? error.message : t("保存失败", "Save failed") }); }
    finally { setSaving(false); }
  };

  const edit = () => { setDraft({ ...config, EMBEDDING_API_KEY: "" }); setStatus(null); setShowKey(false); setOpen(true); };

  return <>
    <section className="ui-card lg:col-span-2" aria-labelledby="embedding-config-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="swiss-kicker text-primary">Knowledge retrieval</p><h3 id="embedding-config-title" className="mt-1 type-h3 text-ink">{t("Embedding 向量模型", "Embedding model")}</h3><p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">{t("只用于知识库片段索引和 Agent 语义检索，不影响普通搜索或通用聊天。", "Used only for knowledge indexing and Agent semantic retrieval; regular search and general chat do not depend on it.")}</p></div>
        <button type="button" onClick={edit} className="ui-button-primary min-h-10 px-4"><Pencil className="h-4 w-4" />{t("配置向量模型", "Configure model")}</button>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <Metric label={t("模型", "Model")} value={config.EMBEDDING_MODEL || t("未配置", "Not configured")} />
        <Metric label={t("向量维度", "Dimensions")} value={`${dimensions} · ${t("数据库固定", "fixed by storage")}`} />
        <Metric label={t("连接状态", "Connection")} value={configured ? t("已配置", "Configured") : t("待配置", "Setup required")} tone={configured ? "good" : "warning"} />
      </div>
      {status && !open && <p role={status.ok ? "status" : "alert"} className={`mt-3 text-sm ${status.ok ? "text-emerald-600" : "text-rose-600"}`}>{status.text}</p>}
    </section>

    <AppDialog open={open} onClose={() => !saving && !testing && setOpen(false)} busy={saving || testing} title={t("配置 Embedding 模型", "Configure embedding model")} description={t("使用 OpenAI 兼容的 Embeddings API。保存前会验证接口与向量维度。", "Use an OpenAI-compatible Embeddings API. The endpoint and vector size are checked before saving.")} className="w-[min(42rem,calc(100vw-2rem))]" footer={<><button type="button" disabled={saving || testing} onClick={() => setOpen(false)} className="ui-button-secondary">{t("取消", "Cancel")}</button><button type="submit" form="embedding-form" disabled={saving || testing} className="ui-button-primary">{saving && <Loader2 className="h-4 w-4 animate-spin" />}{saving ? t("保存中…", "Saving…") : t("保存", "Save")}</button></>}>
      <form id="embedding-form" onSubmit={save} className="space-y-4">
        <label htmlFor="embedding-url" className="block text-sm font-medium text-ink-secondary">{t("Embeddings 接口地址", "Embeddings endpoint URL")}<input id="embedding-url" type="url" required value={draft.EMBEDDING_API_URL} onChange={event => setDraft(current => ({ ...current, EMBEDDING_API_URL: event.target.value }))} placeholder="https://api.example.com/v1/embeddings" className="ui-input mt-2 min-h-11 w-full px-3 text-sm font-normal" /></label>
        <label htmlFor="embedding-model" className="block text-sm font-medium text-ink-secondary">{t("模型名称", "Model name")}<input id="embedding-model" required value={draft.EMBEDDING_MODEL} onChange={event => setDraft(current => ({ ...current, EMBEDDING_MODEL: event.target.value }))} placeholder="bge-m3" className="ui-input mt-2 min-h-11 w-full px-3 text-sm font-normal" /></label>
        <div><label htmlFor="embedding-key" className="block text-sm font-medium text-ink-secondary">API Key</label><div className="ui-input mt-2 flex min-h-11 items-center px-3"><KeyRound className="mr-2 h-4 w-4 shrink-0 text-ink-muted" /><input id="embedding-key" type={showKey ? "text" : "password"} value={draft.EMBEDDING_API_KEY} onChange={event => setDraft(current => ({ ...current, EMBEDDING_API_KEY: event.target.value }))} placeholder={configured ? t("留空以保留当前 Key", "Leave blank to keep current key") : t("请输入 API Key", "Enter API key")} autoComplete="new-password" className="min-w-0 flex-1 bg-transparent text-sm outline-none" /><button type="button" aria-label={showKey ? t("隐藏密钥", "Hide key") : t("显示密钥", "Show key")} onClick={() => setShowKey(value => !value)} className="min-h-9 min-w-9 text-ink-muted">{showKey ? <EyeOff className="mx-auto h-4 w-4" /> : <Eye className="mx-auto h-4 w-4" />}</button></div></div>
        <p className="rounded-xl border border-warning/30 bg-warning/5 p-3 text-xs leading-5 text-ink-secondary"><Search className="mr-1 inline h-3.5 w-3.5" />{t(`当前数据库固定为 ${dimensions} 维。更换模型会改变向量空间，已有索引需要重建后再检索。`, `Storage is fixed at ${dimensions} dimensions. Changing models changes vector space; existing indexes must be rebuilt before retrieval.`)}</p>
        {status && <p role={status.ok ? "status" : "alert"} className={`text-sm ${status.ok ? "text-emerald-600" : "text-rose-600"}`}>{status.ok && <CheckCircle2 className="mr-1 inline h-4 w-4" />}{status.text}</p>}
        <button type="button" disabled={testing || saving} onClick={testConnection} className="ui-button-secondary min-h-11 w-full">{testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlugZap className="h-4 w-4" />}{testing ? t("测试中…", "Testing…") : t("测试连接与维度", "Test connection and dimensions")}</button>
      </form>
    </AppDialog>
  </>;
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "good" | "warning" }) {
  return <div className="min-w-0 rounded-xl bg-surface-subtle p-3"><p className="text-xs text-ink-muted">{label}</p><p className={`mt-1 truncate text-sm font-semibold ${tone === "good" ? "text-emerald-600" : tone === "warning" ? "text-warning" : "text-ink"}`}>{value}</p></div>;
}
