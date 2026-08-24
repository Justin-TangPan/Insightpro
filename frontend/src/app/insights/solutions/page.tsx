"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpRight, ChevronRight, Clock3, Layers3, RefreshCw, Sparkles } from "lucide-react";
import { SectionHeader } from "@/components/section-header";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

interface SolutionItem {
  id: number;
  title: string;
  url: string;
  category: string;
  source_description: string;
  summary: string;
  first_seen_date: string;
  last_seen_date: string;
  last_changed_date: string;
  is_recent: boolean;
  change_type: "new" | "updated";
}

interface SolutionResponse {
  items: SolutionItem[];
  count: number;
  recent_count: number;
  last_checked: string | null;
  source: string;
}

const ALIYUN_DIRECTORY = [
  ["AI", ["模型推理与调用", "模型训练与部署", "模型应用与工具"]],
  ["互联网应用开发", ["网站搭建", "网站性能优化", "短视频与直播", "应用架构", "搜索与推荐"]],
  ["大数据", ["数据分析与智能应用", "数据存储与湖仓构建", "数据处理与计算引擎"]],
  ["安全", ["合规与审计", "应用安全", "数据安全", "账号管理", "办公安全"]],
  ["网络", ["云网络架构设计", "网络优化", "网络高可用", "网络安全"]],
  ["可观测", ["日志管理", "应用监控", "网络监控", "云资源监控"]],
  ["上云与迁云", ["上云", "迁云", "数据迁移"]],
  ["企业出海", ["分类入口", "通用解决方案", "出海行业解决方案", "权益及资源"]],
  ["政企业务", ["分类入口"]],
] as const;

const categoryRank = (root: string, category?: string) => {
  const configured = ALIYUN_DIRECTORY.find(([name]) => name === root);
  const categories: readonly string[] = configured?.[1] || [];
  const rank = category ? categories.indexOf(category) : ALIYUN_DIRECTORY.findIndex(([name]) => name === root);
  return rank < 0 ? 99 : rank;
};

export default function SolutionInsightsPage() {
  const [data, setData] = useState<SolutionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [selectedRoot, setSelectedRoot] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API}/api/solutions/aliyun`);
      if (!response.ok) throw new Error(`加载失败：${response.status}`);
      setData(await response.json());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "解决方案数据加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    setError("");
    try {
      const response = await authenticatedFetch(`${API}/api/solutions/aliyun/refresh`, { method: "POST" });
      if (!response.ok) throw new Error(response.status === 401 ? "请先登录后手动检查更新" : `检查失败：${response.status}`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "检查更新失败");
    } finally {
      setRefreshing(false);
    }
  };

  const directory = useMemo(() => {
    const roots = new Map<string, Map<string, SolutionItem[]>>();
    for (const item of data?.items || []) {
      const [root, category = "分类入口"] = item.category.split(" / ");
      if (!roots.has(root)) roots.set(root, new Map());
      const categories = roots.get(root)!;
      if (!categories.has(category)) categories.set(category, []);
      categories.get(category)!.push(item);
    }
    return Array.from(roots, ([name, categories]) => ({
      name,
      count: Array.from(categories.values()).reduce((total, items) => total + items.length, 0),
      categories: Array.from(categories, ([category, items]) => ({ name: category, items }))
        .sort((a, b) => categoryRank(name, a.name) - categoryRank(name, b.name)),
    })).sort((a, b) => categoryRank(a.name) - categoryRank(b.name));
  }, [data]);
  const activeRoot = directory.some((group) => group.name === selectedRoot) ? selectedRoot : directory[0]?.name || "";
  const activeDirectory = directory.find((group) => group.name === activeRoot);

  return (
    <div className="space-y-8">
      <SectionHeader
        badge="Solution Intelligence"
        title="解决方案洞察"
        subtitle="完整跟踪阿里云技术解决方案 · 用一句话看懂方案价值 · 新增与变更内容自动置顶"
        action={
          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-2 text-xs text-ink-muted">
              <Clock3 className="h-3.5 w-3.5" />
              每天 09:00 自动检查
            </div>
            <button
              type="button"
              onClick={refresh}
              disabled={refreshing}
              className="flex items-center gap-2 bg-ink px-4 py-2 text-xs font-semibold text-paper transition-colors hover:bg-signal disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? "正在检查" : "立即检查更新"}
            </button>
          </div>
        }
      />

      <div className="grid gap-px border border-grid bg-grid sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "当前方案", value: data?.count ?? 0, unit: "项" },
          { label: "近 7 日更新", value: data?.recent_count ?? 0, unit: "项" },
          { label: "一级领域", value: directory.length, unit: "类" },
          { label: "最近检查", value: data?.last_checked?.slice(5) || "—", unit: "日期" },
        ].map((stat) => (
          <div key={stat.label} className="bg-white p-5">
            <p className="swiss-kicker text-ink-muted">{stat.label}</p>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="serif-stat text-3xl text-ink">{stat.value}</span>
              <span className="text-xs text-ink-muted">{stat.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div role="alert" className="border-l-4 border-signal bg-white px-5 py-4 text-sm text-ink-secondary">
          {error}。系统仍会在每天 09:00 自动检查。
        </div>
      )}

      <section className="border border-grid bg-white">
        <div className="flex flex-col gap-4 border-b border-grid px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="swiss-kicker text-signal">Change-first catalog</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-ink">阿里云技术解决方案全量目录</h2>
          </div>
          {data?.source && (
            <a
              href={data.source}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 text-xs font-semibold text-ink-muted hover:text-signal focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
            >
              查看官方来源 <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
          )}
        </div>

        {loading ? (
          <div className="grid gap-px bg-grid md:grid-cols-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-52 animate-shimmer bg-white" />
            ))}
          </div>
        ) : activeDirectory ? (
          <div className="grid lg:grid-cols-[240px_minmax(0,1fr)]">
            <div className="border-b border-grid bg-paper p-4 lg:hidden">
              <label htmlFor="solution-category" className="swiss-kicker text-ink-muted">选择一级领域</label>
              <select
                id="solution-category"
                value={activeRoot}
                onChange={(event) => setSelectedRoot(event.target.value)}
                className="mt-2 w-full border border-grid bg-white px-3 py-2.5 text-sm font-semibold text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
              >
                {directory.map((group) => <option key={group.name} value={group.name}>{group.name}（{group.count}）</option>)}
              </select>
            </div>

            <aside className="hidden border-r border-grid bg-paper lg:block" aria-label="阿里云解决方案一级分类">
              <div className="sticky top-6 p-4">
                <p className="px-3 pb-3 swiss-kicker text-ink-muted">官方分类</p>
                <nav className="space-y-1">
                  {directory.map((group) => {
                    const active = group.name === activeRoot;
                    return (
                      <button
                        key={group.name}
                        type="button"
                        onClick={() => setSelectedRoot(group.name)}
                        aria-current={active ? "page" : undefined}
                        className={`flex w-full items-center justify-between border-l-4 px-3 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal ${active ? "border-signal bg-white text-ink" : "border-transparent text-ink-muted hover:bg-white hover:text-ink"}`}
                      >
                        <span className="text-sm font-bold">{group.name}</span>
                        <span className="flex items-center gap-1 text-xs tabular-nums">
                          {group.count}<ChevronRight className={`h-3.5 w-3.5 ${active ? "text-signal" : ""}`} />
                        </span>
                      </button>
                    );
                  })}
                </nav>
              </div>
            </aside>

            <div className="min-w-0">
              <header className="border-b border-grid bg-ink px-6 py-7 text-paper">
                <p className="swiss-kicker text-lemon">Aliyun directory</p>
                <div className="mt-2 flex items-end justify-between gap-4">
                  <h3 className="text-3xl font-bold tracking-tight">{activeDirectory.name}</h3>
                  <span className="serif-stat text-4xl text-paper/40">{activeDirectory.count}</span>
                </div>
                <p className="mt-2 text-sm text-paper/60">按阿里云原生二级目录浏览，共 {activeDirectory.categories.length} 个分类</p>
              </header>

              {activeDirectory.categories.map((category) => (
                <section key={category.name}>
                  <div className="flex items-center justify-between border-b border-grid bg-paper px-6 py-4">
                    <h4 className="text-lg font-bold text-ink">{category.name}</h4>
                    <span className="text-xs font-semibold tabular-nums text-ink-muted">{category.items.length} 项</span>
                  </div>
                  <div className="grid gap-px bg-grid xl:grid-cols-2">
                    {category.items.map((item) => (
                      <article
                        key={item.url}
                        className={`relative bg-white p-6 transition-colors hover:bg-paper ${item.is_recent ? "border-l-4 border-signal" : "border-l-4 border-transparent"}`}
                      >
                        <div className="flex min-h-7 items-start justify-between gap-5">
                          <p className="swiss-kicker text-ink-muted">{category.name}</p>
                          {item.is_recent && (
                            <span className="flex shrink-0 items-center gap-1 bg-signal px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-white">
                              <Sparkles className="h-3 w-3" />
                              {item.change_type === "new" ? "新增置顶" : "更新置顶"}
                            </span>
                          )}
                        </div>
                        <h5 className="mt-3 text-xl font-bold leading-snug tracking-tight text-ink">{item.title}</h5>
                        <p className="mt-4 border-l-2 border-lemon pl-3 text-base font-semibold leading-relaxed text-ink-secondary">
                          {item.summary}
                        </p>
                        {item.source_description && <p className="mt-3 line-clamp-2 text-sm leading-6 text-ink-muted">{item.source_description}</p>}
                        <div className="mt-6 flex items-center justify-between border-t border-grid pt-4">
                          <span className="text-[11px] text-ink-muted">最近变化 {item.last_changed_date}</span>
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noreferrer"
                            aria-label={`查看阿里云方案：${item.title}`}
                            className="flex items-center gap-1.5 text-xs font-semibold text-ink hover:text-signal focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
                          >
                            查看方案 <ArrowUpRight className="h-3.5 w-3.5" />
                          </a>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex min-h-64 flex-col items-center justify-center gap-3 px-6 text-center">
            <Layers3 className="h-8 w-8 text-ink-muted" />
            <p className="font-semibold text-ink">尚未采集到解决方案</p>
            <p className="text-sm text-ink-muted">登录后点击“立即检查更新”，或等待每天 09:00 自动采集。</p>
          </div>
        )}
      </section>
    </div>
  );
}
