"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight, Clock3, Layers3, RefreshCw, Sparkles,
} from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

interface SolutionItem {
  id: number;
  title: string;
  url: string;
  category: string;
  primary_category: string;
  secondary_category: string;
  source_description: string;
  summary: string;
  vendor: string;
  change_summary: string;
  first_seen_date: string;
  last_seen_date: string;
  last_changed_date: string;
  is_baseline: boolean;
  menu_order: number;
  is_recent: boolean;
  change_type: "new" | "updated";
}

interface SolutionResponse {
  items: SolutionItem[];
  count: number;
  recent_count: number;
  baseline_count: number;
  daily_insight: { date: string; new: number; updated: number; removed: number };
  last_checked: string | null;
  sources: Record<string, string>;
}

const PAGE_SIZE = 12;

export default function SolutionInsightsPage() {
  const [data, setData] = useState<SolutionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [selectedPrimary, setSelectedPrimary] = useState("");
  const [selectedSecondary, setSelectedSecondary] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API}/api/solutions/catalog`);
      if (!response.ok) throw new Error(`加载失败：${response.status}`);
      setData(await response.json());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "解决方案数据加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    setError("");
    try {
      const response = await authenticatedFetch(`${API}/api/solutions/catalog/refresh`, { method: "POST" });
      if (!response.ok) throw new Error(response.status === 401 ? "请先登录后手动检查更新" : `检查失败：${response.status}`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "检查更新失败");
    } finally {
      setRefreshing(false);
    }
  };

  const directory = useMemo(() => {
    const primaryMap = new Map<string, Map<string, SolutionItem[]>>();
    for (const item of data?.items || []) {
      const primary = `${item.vendor} · ${item.primary_category}`;
      if (!primaryMap.has(primary)) primaryMap.set(primary, new Map());
      const secondaryMap = primaryMap.get(primary)!;
      if (!secondaryMap.has(item.secondary_category)) secondaryMap.set(item.secondary_category, []);
      secondaryMap.get(item.secondary_category)!.push(item);
    }
    return Array.from(primaryMap, ([name, secondaryMap]) => ({
      name,
      count: Array.from(secondaryMap.values()).reduce((total, items) => total + items.length, 0),
      order: Math.min(...Array.from(secondaryMap.values()).flat().map((item) => item.menu_order)),
      secondary: Array.from(secondaryMap, ([secondaryName, items]) => ({
        name: secondaryName,
        items,
        order: Math.min(...items.map((item) => item.menu_order)),
      })).sort((a, b) => a.order - b.order),
    })).sort((a, b) => a.order - b.order);
  }, [data]);

  const activePrimary = directory.find((group) => group.name === selectedPrimary) || directory[0];
  const activeSecondary = activePrimary?.secondary.find((group) => group.name === selectedSecondary) || activePrimary?.secondary[0];
  const newItems = (data?.items || []).filter((item) => item.is_recent && item.change_type === "new");
  const totalPages = Math.max(1, Math.ceil((activeSecondary?.items.length || 0) / PAGE_SIZE));
  const activePage = Math.min(currentPage, totalPages);
  const pageStart = (activePage - 1) * PAGE_SIZE;
  const pageItems = activeSecondary?.items.slice(pageStart, pageStart + PAGE_SIZE) || [];

  const selectPrimary = (name: string) => {
    setSelectedPrimary(name);
    setSelectedSecondary("");
    setCurrentPage(1);
  };

  const selectSecondary = (name: string) => {
    setSelectedSecondary(name);
    setCurrentPage(1);
  };

  const changePage = (page: number) => {
    setCurrentPage(page);
    requestAnimationFrame(() => document.getElementById("solution-page")?.scrollIntoView({ block: "start" }));
  };

  return (
    <div className="page-stack">
      <SectionHeader
        badge="Solution Intelligence / Cloud"
        title="解决方案洞察"
        subtitle="汇集阿里云、华为云官方解决方案目录，每日与上一版内容逐项比较。"
        action={
          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-2 text-xs text-ink-muted"><Clock3 className="h-3.5 w-3.5" />每天 09:00 自动对比 · 最近检查 {data?.last_checked || "—"}</div>
            <button type="button" onClick={refresh} disabled={refreshing} className="ui-button-primary">
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? "正在对比" : "立即对比更新"}
            </button>
          </div>
        }
      />

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="今日目录变化">
        {[
          { label: "官方方案", value: data?.count ?? 0, unit: "项" },
          { label: "今日新增", value: data?.daily_insight?.new ?? 0, unit: "项", warning: true },
          { label: "今日更新", value: data?.daily_insight?.updated ?? 0, unit: "项" },
          { label: "今日下线", value: data?.daily_insight?.removed ?? 0, unit: "项" },
        ].map((stat) => (
          <div key={stat.label} className="ui-card flex min-h-36 flex-col justify-end">
            <p className="swiss-kicker text-ink-muted">{stat.label}</p>
            <div className="mt-2 flex items-baseline gap-2"><span className={`serif-stat text-3xl ${stat.warning && stat.value ? "text-warning" : "text-ink"}`}>{stat.value}</span><span className="text-xs text-ink-muted">{stat.unit}</span></div>
          </div>
        ))}
      </section>

      <div className="rounded-xl bg-surface-subtle px-5 py-4 text-sm leading-6 text-ink-secondary">
        当前 {data?.baseline_count ?? 0} 项存量方案已设为普通基线。此后每日按 URL 和内容指纹与上一版比较；更新卡片会列出名称、分类、简介或正文的具体变化。
      </div>

      {error && <div role="alert" className="rounded-xl bg-warning-soft px-5 py-4 text-sm text-warning">{error}。系统仍会在每天 09:00 自动检查。</div>}

      {!loading && newItems.length > 0 && (
        <section className="rounded-2xl bg-warning-soft p-3 sm:p-5">
          <div className="flex items-end justify-between gap-4 px-2 pb-4">
            <div><p className="swiss-kicker text-warning">New since previous catalog</p><h2 className="mt-1 type-h2 text-ink">新增方案置顶</h2></div>
            <span className="ui-tag ui-tag-warning">{newItems.length} 项</span>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">{newItems.map((item) => <SolutionCard key={item.url} item={item} />)}</div>
        </section>
      )}

      <section className="overflow-hidden rounded-2xl bg-white shadow-[var(--shadow-card)]">
        <div className="flex flex-col gap-4 bg-surface-subtle px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="swiss-kicker text-primary">Official directory</p><h2 className="mt-1 type-h2 text-ink">云厂商技术解决方案目录</h2></div>
          <div className="flex gap-3">{Object.entries(data?.sources || {}).map(([vendor, url]) => <a key={vendor} href={url} target="_blank" rel="noreferrer" className="ui-link flex items-center gap-1 text-xs">{vendor}<ArrowUpRight className="h-3.5 w-3.5" /></a>)}</div>
        </div>

        {loading ? (
          <div className="grid gap-3 bg-paper p-3 md:grid-cols-2">{Array.from({ length: 6 }).map((_, index) => <div key={index} className="h-52 animate-shimmer rounded-xl bg-white" />)}</div>
        ) : activePrimary && activeSecondary ? (
          <>
            <div className="grid gap-3 bg-surface-subtle p-4 lg:hidden">
              <label className="block"><span className="swiss-kicker text-ink-muted">一级领域</span><select value={activePrimary.name} onChange={(event) => selectPrimary(event.target.value)} className="ui-input mt-2 w-full px-3 py-2.5 text-sm font-semibold">{directory.map((group) => <option key={group.name} value={group.name}>{group.name}（{group.count}）</option>)}</select></label>
              <label className="block"><span className="swiss-kicker text-ink-muted">二级领域</span><select value={activeSecondary.name} onChange={(event) => selectSecondary(event.target.value)} className="ui-input mt-2 w-full px-3 py-2.5 text-sm font-semibold">{activePrimary.secondary.map((group) => <option key={group.name} value={group.name}>{group.name}（{group.items.length}）</option>)}</select></label>
            </div>

            <div className="grid lg:grid-cols-[190px_230px_minmax(0,1fr)]">
              <aside className="hidden bg-surface-subtle p-3 lg:block" aria-label="一级领域">
                <p className="px-3 pb-3 swiss-kicker text-ink-muted">一级领域 · {directory.length}</p>
                <nav className="space-y-1">{directory.map((group) => {
                  const active = group.name === activePrimary.name;
                  return <button key={group.name} type="button" onClick={() => selectPrimary(group.name)} aria-current={active ? "page" : undefined} className={`flex w-full items-center justify-between rounded-lg px-3 py-3 text-left transition-colors ${active ? "bg-white text-primary shadow-[var(--shadow-card)]" : "text-ink-muted hover:bg-white/70 hover:text-ink"}`}><span className="text-sm font-bold">{group.name}</span><span className="text-xs tabular-nums">{group.count}</span></button>;
                })}</nav>
              </aside>

              <aside className="hidden bg-paper p-3 lg:block" aria-label="二级领域">
                <p className="px-3 pb-3 swiss-kicker text-primary">二级领域 · {activePrimary.secondary.length}</p>
                <nav className="space-y-1">{activePrimary.secondary.map((group) => {
                  const active = group.name === activeSecondary.name;
                  return <button key={group.name} type="button" onClick={() => selectSecondary(group.name)} aria-current={active ? "page" : undefined} className={`flex w-full items-center justify-between rounded-lg px-3 py-3 text-left transition-colors ${active ? "bg-primary-dark text-white" : "bg-white text-ink-secondary hover:bg-primary-soft hover:text-primary"}`}><span className="text-sm font-semibold">{group.name}</span><span className={`text-xs tabular-nums ${active ? "text-white/60" : "text-ink-muted"}`}>{group.items.length}</span></button>;
                })}</nav>
              </aside>

              <div className="min-w-0">
                <header id="solution-page" className="scroll-mt-20 bg-primary-dark px-6 py-7 text-white">
                  <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-white/60">{activePrimary.name} / Secondary domain</p>
                  <div className="mt-2 flex items-end justify-between gap-4"><h3 className="type-h2">{activeSecondary.name}</h3><span className="serif-stat text-4xl text-white/35">{activeSecondary.items.length}</span></div>
                  <p className="mt-2 text-sm text-white/65">顺序与官方目录保持一致 · 第 {activePage}/{totalPages} 页 · 每页 {PAGE_SIZE} 项</p>
                </header>
                <div className="grid gap-2 bg-paper p-2 xl:grid-cols-2">{pageItems.map((item) => <SolutionCard key={item.url} item={item} />)}</div>
                <Pagination page={activePage} totalPages={totalPages} totalItems={activeSecondary.items.length} start={pageStart} onChange={changePage} />
              </div>
            </div>
          </>
        ) : (
          <div className="flex min-h-64 flex-col items-center justify-center gap-3 px-6 text-center"><Layers3 className="h-8 w-8 text-ink-muted" /><p className="font-semibold text-ink">尚未采集到解决方案</p><p className="text-sm text-ink-muted">登录后点击“立即对比更新”，或等待每天 09:00 自动采集。</p></div>
        )}
      </section>
    </div>
  );
}

function Pagination({ page, totalPages, totalItems, start, onChange }: { page: number; totalPages: number; totalItems: number; start: number; onChange: (page: number) => void }) {
  if (totalPages <= 1) return null;
  return (
    <nav aria-label="解决方案分页" className="flex flex-col gap-3 bg-surface-subtle px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs text-ink-muted">显示 {start + 1}–{Math.min(start + PAGE_SIZE, totalItems)} 项，共 {totalItems} 项</p>
      <div className="flex flex-wrap items-center gap-1.5">
        <button type="button" disabled={page === 1} onClick={() => onChange(page - 1)} className="ui-button-secondary px-3 py-2 text-xs">上一页</button>
        {Array.from({ length: totalPages }, (_, index) => index + 1).map((number) => (
          <button key={number} type="button" onClick={() => onChange(number)} aria-current={number === page ? "page" : undefined} aria-label={`第 ${number} 页`} className={`flex h-8 min-w-8 items-center justify-center rounded-lg px-2 font-mono text-xs font-semibold transition-colors ${number === page ? "bg-primary text-white" : "bg-white text-ink-muted hover:bg-primary-soft hover:text-primary"}`}>{number}</button>
        ))}
        <button type="button" disabled={page === totalPages} onClick={() => onChange(page + 1)} className="ui-button-secondary px-3 py-2 text-xs">下一页</button>
      </div>
    </nav>
  );
}

function SolutionCard({ item }: { item: SolutionItem }) {
  return (
    <article className="relative rounded-xl bg-white p-6 transition-all hover:shadow-[var(--shadow-card)]">
      <div className="flex min-h-7 items-start justify-between gap-5">
        <p className="swiss-kicker text-ink-muted">{item.vendor} / {item.primary_category} / {item.secondary_category}</p>
        {item.is_recent && <span className="ui-tag ui-tag-warning shrink-0 gap-1 uppercase tracking-wider"><Sparkles className="h-3 w-3" />{item.change_type === "new" ? "新增置顶" : "内容更新"}</span>}
      </div>
      <h3 className="mt-3 type-h3 text-ink">{item.title}</h3>
      <p className="mt-4 border-l-2 border-lemon pl-3 text-base font-semibold leading-relaxed text-ink-secondary">{item.summary}</p>
      {item.source_description && <p className="mt-3 line-clamp-2 text-sm leading-6 text-ink-muted">{item.source_description}</p>}
      {item.is_recent && item.change_type === "updated" && item.change_summary && <p className="mt-3 rounded-lg bg-warning-soft px-3 py-2 text-xs leading-5 text-warning">{item.change_summary}</p>}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-grid pt-4">
        <span className="text-[11px] text-ink-muted">{item.is_baseline ? "普通方案" : `最近变化 ${item.last_changed_date}`}</span>
        <div className="flex items-center gap-3">
          <Link href={`/insight-agent?context_type=cloud_solution&context_id=${item.id}`} className="ui-button-secondary px-3 py-2 text-xs">Agent 分析</Link>
          <Link href={{ pathname: "/workbench/requirements/new", query: { source_type: "cloud_solution", source_id: String(item.id), source_url: item.url, title: item.title } }} className="ui-button-secondary px-3 py-2 text-xs">创建需求</Link>
          <a href={item.url} target="_blank" rel="noreferrer" aria-label={`查看${item.vendor}方案：${item.title}`} className="ui-link flex items-center gap-1.5 text-xs">查看方案<ArrowUpRight className="h-3.5 w-3.5" /></a>
        </div>
      </div>
    </article>
  );
}
