"use client";

import { SectionHeader } from "@/components/section-header";
import { useCallback, useState, useEffect } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  FileText, Trash2, Plus, Loader2, AlertCircle,
  CheckCircle2, Clock, Search, RefreshCw
} from "lucide-react";

interface Report {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ReportResult {
  summary_metrics?: Record<string, unknown>;
  takeaways?: unknown[];
  detailed_report?: string;
  strategies?: unknown;
  [key: string]: unknown;
}

interface ReportDetail extends Report {
  result?: ReportResult;
  error?: string;
  data_sources?: unknown[];
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newKeyword, setNewKeyword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;

  // Fetch reports list
  const fetchReports = useCallback(async () => {
    try {
      const res = await authenticatedFetch(`${API}/api/reports?page=${page}&page_size=${pageSize}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setReports(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to fetch reports:", err);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    void Promise.resolve().then(fetchReports);
  }, [fetchReports]);

  // Poll task status after submission
  useEffect(() => {
    if (!taskId || taskStatus === "completed" || taskStatus === "failed") return;
    const interval = setInterval(async () => {
      try {
        const res = await authenticatedFetch(`${API}/api/tasks/${taskId}`);
        if (!res.ok) return;
        const data = await res.json();
        setTaskStatus(data.status);
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
          void fetchReports();
          if (data.status === "completed") {
            setSelectedId(taskId);
          }
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [fetchReports, taskId, taskStatus]);

  // Fetch detail when selected
  useEffect(() => {
    void Promise.resolve().then(() => {
      if (!selectedId) {
        setDetail(null);
        return;
      }
      setDetailLoading(true);
      authenticatedFetch(`${API}/api/reports/${selectedId}`)
        .then(res => res.json())
        .then((data: ReportDetail) => setDetail(data))
        .catch(console.error)
        .finally(() => setDetailLoading(false));
    });
  }, [selectedId]);

  // Submit new analysis
  const handleSubmit = async () => {
    if (!newTitle || !newKeyword) return;
    setSubmitting(true);
    try {
      const res = await authenticatedFetch(`${API}/api/tasks/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: newTitle,
          data_sources: [{ type: "KEYWORD", content: newKeyword }],
          depth: "standard",
        }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setTaskId(data.task_id);
      setTaskStatus("processing");
      setShowNew(false);
      setNewTitle("");
      setNewKeyword("");
    } catch (err) {
      console.error("Failed to submit analysis:", err);
    } finally {
      setSubmitting(false);
    }
  };

  // Delete report
  const handleDelete = async (id: string) => {
    try {
      await authenticatedFetch(`${API}/api/reports/${id}`, { method: "DELETE" });
      if (selectedId === id) { setSelectedId(null); setDetail(null); }
      void fetchReports();
    } catch (err) {
      console.error("Failed to delete report:", err);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed": return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case "processing": return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case "failed": return <AlertCircle className="h-4 w-4 text-red-500" />;
      default: return <Clock className="h-4 w-4 text-ink-muted" />;
    }
  };

  const statusLabel: Record<string, string> = {
    pending: "等待中", processing: "分析中", completed: "已完成", failed: "失败"
  };

  const formatDate = (d: string) => {
    try { return new Date(d).toLocaleString("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
    catch { return d; }
  };

  // Render AI report content
  const renderReportContent = (result: ReportResult | undefined) => {
    if (!result) return <p className="text-ink-muted">无报告内容</p>;
    const summaryMetrics = result.summary_metrics;
    // If result has structured fields
    if (result.summary_metrics || result.takeaways || result.detailed_report || result.strategies) {
      return (
        <div className="space-y-6">
          {summaryMetrics && (
            <div>
              <h4 className="text-sm font-semibold text-ink mb-3">市场指标</h4>
              <div className="grid grid-cols-3 gap-3">
                {Object.entries(summaryMetrics).map(([k, v]) => (
                  <div key={k} className="bg-slate-50 border border-slate-200/60 rounded-lg p-3 text-center">
                    <p className="text-xs text-ink-muted mb-1">{k}</p>
                    <p className="text-lg font-bold text-ink">{typeof v === "number" ? v : String(v)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {Array.isArray(result.takeaways) && (
            <div>
              <h4 className="text-sm font-semibold text-ink mb-3">核心结论</h4>
              <div className="space-y-2">
                {result.takeaways.map((t, i) => (
                  <div key={i} className="bg-white border border-slate-200/60 rounded-lg p-4">
                    <p className="text-sm text-ink-secondary leading-relaxed">{typeof t === "string" ? t : JSON.stringify(t)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {typeof result.detailed_report === "string" && result.detailed_report && (
            <div>
              <h4 className="text-sm font-semibold text-ink mb-3">详细报告</h4>
              <div className="prose prose-slate max-w-none bg-white border border-slate-200/60 rounded-lg p-6">
                <p className="text-sm text-ink-secondary leading-relaxed whitespace-pre-wrap">{result.detailed_report}</p>
              </div>
            </div>
          )}
          {Boolean(result.strategies) && (
            <div>
              <h4 className="text-sm font-semibold text-ink mb-3">战略建议</h4>
              <div className="bg-white border border-slate-200/60 rounded-lg p-4">
                <p className="text-sm text-ink-secondary leading-relaxed whitespace-pre-wrap">
                  {typeof result.strategies === "string" ? result.strategies : JSON.stringify(result.strategies, null, 2)}
                </p>
              </div>
            </div>
          )}
        </div>
      );
    }
    // Fallback: render raw JSON
    return (
      <div className="bg-white border border-slate-200/60 rounded-lg p-6">
        <pre className="text-sm text-ink-secondary leading-relaxed whitespace-pre-wrap overflow-auto">
          {JSON.stringify(result, null, 2)}
        </pre>
      </div>
    );
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      <SectionHeader
        badge="Reports"
        title="深度研报"
        subtitle="AI 生成的结构化商业分析报告"
        action={
          <button
            onClick={() => setShowNew(true)}
            className="flex items-center gap-2 rounded-lg bg-ink px-5 py-2 text-xs font-semibold text-paper hover:bg-ink-secondary transition-colors"
          >
            <Plus className="h-4 w-4" />
            新建分析
          </button>
        }
      />

      {/* Task processing indicator */}
      {taskId && taskStatus && (
        <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${
          taskStatus === "completed" ? "bg-emerald-50 border-emerald-200" :
          taskStatus === "failed" ? "bg-red-50 border-red-200" :
          "bg-blue-50 border-blue-200"
        }`}>
          {statusIcon(taskStatus)}
          <span className="text-sm font-medium text-ink">
            {taskStatus === "processing" && "AI 正在分析中，请稍候..."}
            {taskStatus === "completed" && "分析完成！"}
            {taskStatus === "failed" && "分析失败，请重试"}
            {taskStatus === "pending" && "任务排队中..."}
          </span>
          {taskStatus === "processing" && <Loader2 className="h-4 w-4 text-blue-500 animate-spin ml-auto" />}
        </div>
      )}

      {/* New analysis form */}
      {showNew && (
        <div className="bg-white border border-slate-200/60 rounded-lg p-6 space-y-4">
          <h3 className="text-sm font-semibold text-ink">新建 AI 分析任务</h3>
          <div>
            <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">分析标题</label>
            <input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="例：2026年新能源汽车市场深度洞察"
              className="w-full px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block mb-1.5">分析关键词 / 背景数据</label>
            <textarea
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              placeholder="输入关键词、行业、竞品名称等，AI 将基于平台数据生成深度分析报告"
              rows={4}
              className="w-full px-3.5 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-ink focus:outline-none focus:border-slate-300 focus:bg-white transition-colors resize-none"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowNew(false)} className="px-4 py-2 rounded-lg text-xs font-medium border border-slate-200 text-ink-secondary hover:bg-slate-50 transition-colors">取消</button>
            <button onClick={handleSubmit} disabled={submitting || !newTitle || !newKeyword} className="flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-semibold bg-ink text-paper hover:bg-ink-secondary transition-colors disabled:opacity-50">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              开始分析
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report List */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-slate-200/60 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
              <h3 className="text-sm font-semibold text-ink">报告列表</h3>
              <button onClick={fetchReports} className="text-ink-muted hover:text-ink transition-colors">
                <RefreshCw className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
              {loading ? (
                <div className="p-6 text-center text-ink-muted text-sm">加载中...</div>
              ) : reports.length === 0 ? (
                <div className="p-6 text-center">
                  <FileText className="h-8 w-8 text-ink-muted mx-auto mb-2" />
                  <p className="text-sm text-ink-muted">暂无报告</p>
                  <p className="text-xs text-ink-muted mt-1">点击&quot;新建分析&quot;生成第一份 AI 研报</p>
                </div>
              ) : (
                reports.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setSelectedId(r.id)}
                    className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors ${selectedId === r.id ? "bg-slate-50 border-l-2 border-l-ink" : ""}`}
                  >
                    <div className="flex items-start gap-2">
                      {statusIcon(r.status)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-ink truncate">{r.title}</p>
                        <p className="text-xs text-ink-muted mt-0.5">{formatDate(r.created_at)}</p>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-2 border-t border-slate-100 text-xs text-ink-muted">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="hover:text-ink disabled:opacity-30">上一页</button>
                <span>{page} / {totalPages}</span>
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="hover:text-ink disabled:opacity-30">下一页</button>
              </div>
            )}
          </div>
        </div>

        {/* Report Detail */}
        <div className="lg:col-span-2">
          {!selectedId ? (
            <div className="bg-white border border-slate-200/60 rounded-lg p-12 text-center">
              <FileText className="h-12 w-12 text-ink-muted mx-auto mb-3" />
              <p className="text-ink-secondary">选择左侧报告查看详情</p>
            </div>
          ) : detailLoading ? (
            <div className="bg-white border border-slate-200/60 rounded-lg p-12 text-center">
              <Loader2 className="h-8 w-8 text-ink-muted mx-auto animate-spin" />
            </div>
          ) : detail ? (
            <div className="bg-white border border-slate-200/60 rounded-lg overflow-hidden">
              {/* Header */}
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    {statusIcon(detail.status)}
                    <span className="text-xs font-medium text-ink-muted">{statusLabel[detail.status] || detail.status}</span>
                    <span className="text-xs text-ink-muted">•</span>
                    <span className="text-xs text-ink-muted">{formatDate(detail.created_at)}</span>
                  </div>
                  <h2 className="text-lg font-semibold text-ink">{detail.title}</h2>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleDelete(detail.id)}
                    className="p-2 rounded-lg hover:bg-red-50 text-ink-muted hover:text-red-500 transition-colors"
                    title="删除报告"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
              {/* Content */}
              <div className="p-6">
                {detail.status === "failed" ? (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertCircle className="h-4 w-4 text-red-500" />
                      <span className="text-sm font-semibold text-red-700">分析失败</span>
                    </div>
                    <p className="text-sm text-red-600">{detail.error || "未知错误"}</p>
                  </div>
                ) : detail.status === "processing" ? (
                  <div className="text-center py-12">
                    <Loader2 className="h-8 w-8 text-blue-500 mx-auto animate-spin mb-3" />
                    <p className="text-sm text-ink-secondary">AI 正在生成分析报告...</p>
                    <p className="text-xs text-ink-muted mt-1">通常需要 30-60 秒</p>
                  </div>
                ) : detail.result ? (
                  renderReportContent(detail.result)
                ) : (
                  <p className="text-ink-muted">无报告内容</p>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
