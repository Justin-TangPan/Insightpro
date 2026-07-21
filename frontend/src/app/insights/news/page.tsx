"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Calendar, ExternalLink, RefreshCw } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";

interface NewsItem {
  id: number;
  crawl_date: string;
  source: string;
  title: string;
  summary?: string;
  url?: string;
}

interface NewsResponse {
  items: NewsItem[];
  count: number;
}

export default function NewsPage() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadNews = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API}/api/industry-news?days=2&limit=50`, { cache: "no-store" });
      if (!response.ok) throw new Error(`API ${response.status}`);
      const data: NewsResponse = await response.json();
      setNews(data.items || []);
    } catch (err) {
      setNews([]);
      setError(err instanceof Error ? err.message : "新闻数据加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(loadNews);
  }, [loadNews]);

  const latestDate = news[0]?.crawl_date;

  return (
    <div className="max-w-5xl mx-auto space-y-10 pb-20">
      <SectionHeader
        badge="商业快讯"
        title="商业快讯实时监测"
        subtitle={latestDate ? `已验证数据 · 最近采集 ${latestDate}` : "仅展示最近 48 小时内通过质量检查的真实数据"}
        image="https://images.unsplash.com/photo-1504711434969-e33886168d6c?w=800&q=80"
        action={
          <button onClick={() => void loadNews()} disabled={loading} className="inline-flex items-center gap-2 border border-grid bg-white px-4 py-2 text-xs font-semibold disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            刷新
          </button>
        }
      />

      {loading && <div className="border border-grid bg-white p-10 text-center text-sm text-ink-muted">正在读取最新数据…</div>}

      {!loading && (error || news.length === 0) && (
        <div className="border border-amber-200 bg-amber-50 p-8 text-center">
          <AlertTriangle className="mx-auto mb-3 h-6 w-6 text-amber-600" />
          <p className="font-semibold text-ink">当前没有满足时效和质量要求的商业快讯</p>
          <p className="mt-2 text-sm text-ink-muted">{error || "系统不会再用五月或六月的静态内容冒充实时新闻。"}</p>
        </div>
      )}

      {!loading && news.length > 0 && (
        <div className="grid gap-6 md:grid-cols-2">
          {news.map((item) => (
            <article key={item.id} className="flex flex-col overflow-hidden rounded-xl border border-slate-200/60 bg-white shadow-[var(--shadow-card)]">
              <div className="flex-1 space-y-4 p-6">
                <div className="flex items-center justify-between gap-3">
                  <span className="inline-flex rounded-full gradient-primary px-3 py-1 text-xs font-semibold text-white">{item.source}</span>
                  <span className="flex items-center gap-1.5 text-xs font-medium text-ink-muted"><Calendar className="h-3 w-3" />{item.crawl_date}</span>
                </div>
                <h3 className="text-lg serif-heading leading-snug text-ink">{item.title}</h3>
                {item.summary && <p className="text-sm leading-relaxed text-ink-secondary">{item.summary}</p>}
              </div>
              <div className="border-t border-slate-100 bg-slate-50 px-6 py-4">
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-xs font-semibold text-primary hover:underline"><ExternalLink className="h-3 w-3" />查看原始来源</a>
                ) : <span className="text-xs text-ink-muted">来源链接不可用</span>}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
