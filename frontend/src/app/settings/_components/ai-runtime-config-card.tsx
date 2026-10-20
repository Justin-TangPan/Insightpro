"use client";

import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Eye, EyeOff, KeyRound, Loader2, Pencil, PlugZap, Sparkles } from "lucide-react";
import { AppDialog } from "@/components/ui";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";

type Config = { CHAT_API_URL: string; CHAT_MODEL: string; CHAT_API_KEY: string };
type Status = { ok: boolean; text: string } | null;
const emptyUsage = { requests: 0, input_tokens: 0, output_tokens: 0, token_requests: 0 };

export function AiRuntimeConfigCard() {
  const { preferences } = usePreferences();
  const t = (zh: string, en: string) => preferences.language === "en" ? en : zh;
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.app_metadata?.role === "admin";
  const [config, setConfig] = useState<Config>({ CHAT_API_URL: "", CHAT_MODEL: "", CHAT_API_KEY: "" });
  const [draft, setDraft] = useState<Config>(config);
  const [usage, setUsage] = useState({ today: emptyUsage, models: [] as { model: string; requests: number; input_tokens: number; output_tokens: number; token_requests: number }[], apiKeyConfigured: false });
  const [models, setModels] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [status, setStatus] = useState<Status>(null);

  const fetchConfig = () => authenticatedFetch(`${API}/api/auth/admin/runtime-config`)
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => {
      const next = { CHAT_API_URL: data.config?.CHAT_API_URL || "", CHAT_MODEL: data.config?.CHAT_MODEL || "", CHAT_API_KEY: "" };
      setConfig(next); setDraft(next);
      setUsage({ today: data.usage?.today || emptyUsage, models: data.usage?.models || [], apiKeyConfigured: Boolean(data.api_key_configured) });
    })
    .catch(() => undefined);

  useEffect(() => { if (!authLoading && isAdmin) void fetchConfig(); }, [authLoading, isAdmin]);

  const request = async (method: "POST" | "PATCH") => {
    const suffix = method === "POST" ? "/verify" : "";
    const response = await authenticatedFetch(`${API}/api/auth/admin/runtime-config${suffix}`, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || t("连接失败，请检查配置", "Connection failed. Check the configuration."));
    setModels(Array.isArray(data.models) ? data.models : []);
    return data;
  };

  const testConnection = async () => {
    setTesting(true); setStatus(null);
    try {
      const data = await request("POST");
      setStatus({ ok: true, text: `${t("连接成功", "Connected")} · ${data.latency_ms} ms${data.models?.length ? ` · ${data.models.length} ${t("个模型", "models")}` : ""}` });
    } catch (error) { setStatus({ ok: false, text: error instanceof Error ? error.message : t("连接失败", "Connection failed") }); }
    finally { setTesting(false); }
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setSaving(true); setStatus(null);
    try {
      const data = await request("PATCH");
      const next = { CHAT_API_URL: data.config.CHAT_API_URL, CHAT_MODEL: data.config.CHAT_MODEL, CHAT_API_KEY: "" };
      setConfig(next); setDraft(next); setUsage(current => ({ ...current, apiKeyConfigured: true }));
      setStatus({ ok: true, text: t("连接已验证，模型配置已保存", "Connection verified and model saved") }); setOpen(false);
    } catch (error) { setStatus({ ok: false, text: error instanceof Error ? error.message : t("保存失败", "Save failed") }); }
    finally { setSaving(false); }
  };

  const edit = () => { setDraft({ ...config, CHAT_API_KEY: "" }); setStatus(null); setShowKey(false); setOpen(true); };
  const tokenCount = usage.today.input_tokens + usage.today.output_tokens;

  return <>
    <section className="ui-card lg:col-span-2" aria-labelledby="model-config-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="swiss-kicker text-primary">Model configuration</p><h3 id="model-config-title" className="mt-1 type-h3 text-ink">{t("模型配置", "Model configuration")}</h3><p className="mt-2 text-sm text-ink-muted">{t("全站生成式 AI 共用当前模型连接。", "All generative AI features use this model connection.")}</p></div>
        <button type="button" onClick={edit} className="ui-button-primary min-h-10 px-4"><Pencil className="h-4 w-4" />{t("编辑模型", "Edit model")}</button>
      </div>
      <div className="mt-6 rounded-2xl border border-grid bg-surface-subtle p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary"><Sparkles className="h-5 w-5" /></span><div className="min-w-0"><p className="truncate text-base font-semibold text-ink">{config.CHAT_MODEL || t("尚未配置模型", "No model configured")}</p><p className="mt-1 truncate text-xs text-ink-muted">{t("自定义 · OpenAI 兼容协议", "Custom · OpenAI-compatible")}</p></div></div>
          <span className={`ui-tag ${usage.apiKeyConfigured ? "ui-tag-success" : "ui-tag-warning"}`}>{usage.apiKeyConfigured ? <><CheckCircle2 className="h-3 w-3" />{t("已配置", "Configured")}</> : t("待配置", "Setup required")}</span>
        </div>
        <p className="mt-4 truncate rounded-xl bg-white px-4 py-3 font-mono text-xs text-ink-muted">{config.CHAT_API_URL || "—"}</p>
        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-ink-muted"><span>{t("今日请求", "Requests today")} <strong className="text-ink">{usage.today.requests}</strong></span><span>Token <strong className="text-ink">{tokenCount}</strong></span><span>{t("近 7 天活跃模型", "Active models, 7d")} <strong className="text-ink">{usage.models.length}</strong></span></div>
      </div>
      {status && !open && <p role={status.ok ? "status" : "alert"} className={`mt-3 text-sm ${status.ok ? "text-emerald-600" : "text-rose-600"}`}>{status.text}</p>}
    </section>

    <AppDialog open={open} onClose={() => !saving && setOpen(false)} busy={saving} title={t("编辑模型", "Edit model")} description={t("配置 OpenAI 兼容接口；保存前会再次验证连接。", "Configure an OpenAI-compatible endpoint. The connection is verified again before saving.")} className="w-[min(42rem,calc(100vw-2rem))]" footer={<><button type="button" disabled={saving || testing} onClick={() => setOpen(false)} className="ui-button-secondary">{t("取消", "Cancel")}</button><button type="submit" form="ai-model-form" disabled={saving || testing} className="ui-button-primary">{saving && <Loader2 className="h-4 w-4 animate-spin" />}{saving ? t("保存中…", "Saving…") : t("保存", "Save")}</button></>}>
      <form id="ai-model-form" onSubmit={save} className="space-y-5">
        <label className="block text-sm font-medium text-ink-secondary">{t("供应商（仅支持 OpenAI 兼容协议 API）", "Provider (OpenAI-compatible APIs only)")}<select value="custom" disabled className="ui-input mt-2 min-h-11 w-full px-3 text-sm font-normal"><option value="custom">✧ {t("自定义", "Custom")}</option></select></label>
        <label htmlFor="ai-base-url" className="block text-sm font-medium text-ink-secondary">{t("接口地址", "Endpoint URL")}<input id="ai-base-url" type="url" required value={draft.CHAT_API_URL} onChange={event => setDraft(current => ({ ...current, CHAT_API_URL: event.target.value }))} placeholder="https://api.example.com/v1" className="ui-input mt-2 min-h-11 w-full px-3 py-2 text-sm font-normal" /><span className="mt-1.5 block text-xs font-normal text-ink-muted">{t("填写 API 根路径，系统会自动调用 /chat/completions。", "Enter the API root; /chat/completions is appended automatically.")}</span></label>
        <div><label htmlFor="ai-api-key" className="block text-sm font-medium text-ink-secondary">API Key</label><div className="mt-2 flex gap-2"><div className="ui-input flex min-h-11 flex-1 items-center px-3"><KeyRound className="mr-2 h-4 w-4 shrink-0 text-ink-muted" /><input id="ai-api-key" type={showKey ? "text" : "password"} value={draft.CHAT_API_KEY} onChange={event => setDraft(current => ({ ...current, CHAT_API_KEY: event.target.value }))} placeholder={usage.apiKeyConfigured ? t("留空以保留当前 Key", "Leave blank to keep current key") : t("请输入 API Key", "Enter API key")} autoComplete="new-password" className="min-w-0 flex-1 bg-transparent text-sm outline-none" /><button type="button" onClick={() => setShowKey(value => !value)} className="p-1 text-ink-muted hover:text-ink" aria-label={showKey ? t("隐藏密钥", "Hide key") : t("显示密钥", "Show key")}>{showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div><button type="button" disabled={testing || saving} onClick={testConnection} className="ui-button-secondary min-h-11 shrink-0 px-4">{testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlugZap className="h-4 w-4" />}{testing ? t("测试中…", "Testing…") : t("测试连接", "Test connection")}</button></div></div>
        <label htmlFor="ai-model" className="block text-sm font-medium text-ink-secondary">{t("模型名称", "Model name")}<input id="ai-model" required list="ai-model-options" value={draft.CHAT_MODEL} onChange={event => setDraft(current => ({ ...current, CHAT_MODEL: event.target.value }))} placeholder="model-name" className="ui-input mt-2 min-h-11 w-full px-3 py-2 text-sm font-normal" /><datalist id="ai-model-options">{models.map(model => <option key={model} value={model} />)}</datalist></label>
        {status && <p role={status.ok ? "status" : "alert"} className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${status.ok ? "bg-emerald-500/10 text-emerald-600" : "bg-rose-500/10 text-rose-600"}`}>{status.ok && <CheckCircle2 className="h-4 w-4" />}{status.text}</p>}
      </form>
    </AppDialog>
  </>;
}
