"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { API } from "@/lib/api";
import { cachedJson, peekJson } from "@/lib/client-data-cache";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import { RefreshCw, Sparkles } from "lucide-react";
import { InsightPageShell } from "@/components/insight-page-shell";
import { communityItems, daysAgo, distribution, keywords, withinLastDays } from "@/lib/insight-dashboard";
import type { BoardInsight, CommunityEvent, CommunityLegacy, History } from "@/lib/insight-dashboard";
import { InsightEmptyState, InsightErrorState, InsightFilterBar, InsightHero, InsightKeywordPanel, InsightList, InsightLoadingState, InsightSection, InsightSourceCard, InsightTopicDistribution, InsightTrendChart } from "@/components/insight-dashboard";
import type { FilterState } from "@/components/insight-dashboard";

type LegacyResponse = { items: CommunityLegacy[]; count: number };
const initialFilters: FilterState = { query: "", owner: "", category: "", topic: "", days: 0, sort: "latest", onlyPriority: false, view: "list" };
const get = <T,>(path: string, force = false): Promise<T> => cachedJson<T>(`${API}${path}`, force);

export default function CommunityInsightsPage() {
  const { user } = useAuth();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [events, setEvents] = useState<CommunityEvent[]>(() => peekJson<{ items: CommunityEvent[] }>(`${API}/api/v2/events?business_scope=community_insights&limit=100`)?.items || []);
  const [legacy, setLegacy] = useState<CommunityLegacy[]>(() => peekJson<LegacyResponse>(`${API}/api/community/insights`)?.items || []);
  const [board, setBoard] = useState<BoardInsight | null>(() => peekJson<BoardInsight>(`${API}/api/boards/community/daily-insight`) || null);
  const [history, setHistory] = useState<History | null>(() => peekJson<History>(`${API}/api/community/insights/history`) || null);
  const [trendDays, setTrendDays] = useState<7 | 30 | 90>(7);
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [limit, setLimit] = useState(24);
  const [loading, setLoading] = useState(() => !peekJson<LegacyResponse>(`${API}/api/community/insights`) && !peekJson(`${API}/api/v2/events?business_scope=community_insights&limit=100`));
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (force = false) => {
    const legacyResult = await get<LegacyResponse>("/api/community/insights", force).catch(() => null);
    void get<BoardInsight>("/api/boards/community/daily-insight", force).then(setBoard).catch(() => setBoard(null));
    void get<History>("/api/community/insights/history", force).then(setHistory).catch(() => setHistory(null));
    const [eventResult] = await Promise.allSettled([
      get<{ items: CommunityEvent[] }>("/api/v2/events?business_scope=community_insights&limit=100", force),
    ]);
    if (eventResult.status === "rejected" && !legacyResult) throw new Error("社区热点加载失败");
    if (eventResult.status === "fulfilled") setEvents(eventResult.value.items || []);
    if (legacyResult) setLegacy(legacyResult.items || []);
    setError("");
  }, []);
  useEffect(() => { let active = true; void Promise.resolve().then(() => load()).catch(reason => { if (active) setError(reason.message); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [load]);
  const all = useMemo(() => communityItems(events, legacy), [events, legacy]);
  const owners = useMemo(() => [...new Set(all.flatMap(item => item.owners || [item.owner]))].sort(), [all]);
  const categories = useMemo(() => [...new Set(all.map(item => item.category))].sort(), [all]);
  const scoped = all.filter(item => (!filters.owner || item.owners?.includes(filters.owner)) && (!filters.days || daysAgo(item.date, filters.days)) && (!filters.query || `${item.title} ${item.summary} ${item.owner} ${item.topic}`.toLowerCase().includes(filters.query.toLowerCase())));
  const topics = distribution(scoped);
  const visible = scoped.filter(item => (!filters.category || item.category === filters.category) && (!filters.onlyPriority || item.priority)).sort((a, b) => filters.sort === "heat" ? (b.heat || 0) - (a.heat || 0) || b.date.localeCompare(a.date) : filters.sort === "priority" ? Number(b.priority) - Number(a.priority) || b.date.localeCompare(a.date) : b.date.localeCompare(a.date));
  const heat = all.reduce((sum, item) => sum + (item.heat || 0), 0);
  const heatCount = all.filter(item => item.heat !== undefined).length;
  const newCount = events.length ? events.filter(item => withinLastDays(item.first_seen_at, 1)).length : legacy.filter(item => withinLastDays(item.observed_at, 1)).length;
  const latest = events.map(item => item.last_seen_at || "").concat(legacy.map(item => item.observed_at || "")).sort().at(-1);
  const sourceCounts = owners.map(name => ({ name, count: all.filter(item => item.owners?.includes(name)).length, points: history?.groups.find(group => group.name === name)?.points }));
  async function refresh() { setRefreshing(true); try { const response = await authenticatedFetch(`${API}/api/community/insights/refresh`, { method: "POST" }); if (!response.ok) throw new Error("刷新失败，请检查登录状态"); await load(true); } catch (reason) { setError(reason instanceof Error ? reason.message : "刷新失败"); } finally { setRefreshing(false); } }
  async function retry() { try { await load(true); } catch (reason) { setError(reason instanceof Error ? reason.message : "加载失败"); } finally { setLoading(false); } }
  const setFilter = (value: FilterState) => { setFilters(value); setLimit(24); };
  const selectOwner = (name: string) => setFilter({ ...filters, owner: filters.owner === name ? "" : name });
  const selectTopic = (name: string) => setFilter({ ...filters, category: filters.category === name ? "" : name });
  return <InsightPageShell artwork="/illustrations/community.png" title={en ? "AI Community Hotspots" : "AI 社区热点"} description={en ? "Track community discussions and extract today’s AI signals." : "聚合社区内容，提炼今日关键洞察，识别 AI 行业趋势与开发者关注焦点。"} icon={<Sparkles size={21} />} range={en ? "Today" : "今日"} updated={latest?.slice(0, 16).replace("T", " ") || ""} status={error ? (en ? "Unavailable" : "读取失败") : refreshing ? (en ? "Updating" : "更新中") : (en ? "Data ready" : "数据已就绪")} metrics={[{ label: en ? "Disclosed heat" : "已披露热度", value: heatCount ? heat.toLocaleString() : "—", note: `${heatCount} ${en ? "records" : "条有热度数据"}` }, { label: en ? "Communities" : "来源社区数", value: owners.length }, { label: en ? "New discussions" : "新增讨论", value: newCount, note: en ? "First seen in 24h" : "首次发现于近 24 小时" }, { label: en ? "Priority topics" : "重点主题", value: all.filter(item => item.priority).length }]} action={<button type="button" className="insight-page-refresh" disabled={refreshing || !user} title={!user ? (en ? "Sign in to refresh" : "登录后可刷新") : undefined} onClick={() => void refresh()}><RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />{refreshing ? (en ? "Refreshing" : "刷新中") : (en ? "Refresh" : "刷新数据")}</button>}>
    <div className="insight-dashboard">
    {error && <InsightErrorState text={error} retry={() => void retry()} />}
    {loading ? <InsightLoadingState /> : <>
      <div className="dash-top"><InsightHero title="今日核心结论" board={board} note="热榜为采集快照；未提供发布时间的话题以发现时间标记。" /><InsightTrendChart title="社区热度趋势" history={history} days={trendDays} setDays={setTrendDays} /></div>
      <InsightSection title="社区来源概览" meta={`${owners.length} 个有情报的来源`}><div className="dash-sources">{sourceCounts.map(item => <InsightSourceCard key={item.name} name={item.name} count={item.count} points={item.points} active={filters.owner === item.name} onClick={() => selectOwner(item.name)} />)}</div>{!owners.length && <InsightEmptyState text="当前没有可展示的社区来源。" />}</InsightSection>
      <div className="dash-content"><div className="dash-main"><InsightSection title="全部 AI 热点" meta={`${visible.length} 条匹配情报`}><InsightFilterBar value={filters} setValue={setFilter} owners={owners} categories={categories} ownerLabel="来源" hasHeat={heatCount > 0} priorityLabel="高价值" /><InsightList items={visible} view={filters.view} showHeat limit={limit} more={() => setLimit(limit + 24)} /></InsightSection></div><aside className="dash-side-stack"><InsightTopicDistribution title="热点主题分布" values={topics} active={filters.category} select={selectTopic} /><InsightKeywordPanel title="今日高频关键词" values={keywords(scoped)} select={word => setFilter({ ...filters, query: word })} /></aside></div>
    </>}
    </div>
  </InsightPageShell>;
}
