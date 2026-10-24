"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { API } from "@/lib/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useAuth } from "@/components/auth-provider";
import { usePreferences } from "@/lib/preferences";
import { competitorItems, daysAgo, distribution, keywords } from "@/lib/insight-dashboard";
import type { BoardInsight, CompetitorNews, History } from "@/lib/insight-dashboard";
import { InsightEmptyState, InsightErrorState, InsightFilterBar, InsightHero, InsightKeywordPanel, InsightList, InsightLoadingState, InsightPageHeader, InsightSection, InsightSourceCard, InsightTopicDistribution, InsightTrendChart } from "@/components/insight-dashboard";
import type { FilterState } from "@/components/insight-dashboard";

type Vendor = { name: string; region: string; products: string[]; strengths: string[]; weaknesses: string[]; vs_huawei: string };
type Event = { id: number; vendor?: string; title: string; summary?: string; published_at?: string; first_seen_at?: string; source_url?: string; categories?: string[]; event_type?: string; scores?: Record<string, number> };
const aliases: Record<string, string> = { Azure: "Microsoft Azure", 火山云: "Volcengine", 火山引擎: "Volcengine" };
const vendorLabel = (name: string, en: boolean) => en ? name : ({ "Alibaba Cloud": "阿里云", "Tencent Cloud": "腾讯云", Volcengine: "火山引擎", "Microsoft Azure": "微软 Azure" }[name] || name);
const initialFilters: FilterState = { query: "", owner: "", category: "", topic: "", days: 0, sort: "latest", onlyPriority: false, view: "list" };
const get = async <T,>(path: string): Promise<T> => { const response = await fetch(`${API}${path}`, { cache: "no-store" }); if (!response.ok) throw new Error(path); return response.json(); };

export default function CompetitorsPage() {
  const { user } = useAuth();
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [profiles, setProfiles] = useState<Vendor[]>([]);
  const [summary, setSummary] = useState<Record<string, CompetitorNews[]>>({});
  const [v2, setV2] = useState<Event[]>([]);
  const [board, setBoard] = useState<BoardInsight | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [updated, setUpdated] = useState("");
  const [trendDays, setTrendDays] = useState<7 | 30 | 90>(7);
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [limit, setLimit] = useState(24);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [profilesResult, summaryResult, eventsResult, boardResult, historyResult] = await Promise.allSettled([
      get<{ vendors: Vendor[]; date: string }>("/api/competitors"),
      get<{ vendors: Record<string, CompetitorNews[]> }>("/api/competitors/summary?limit_per_vendor=100"),
      get<{ items: Event[] }>("/api/v2/events?business_scope=competitor_dynamics&limit=100"),
      get<BoardInsight>("/api/boards/competitors/daily-insight"),
      get<History>("/api/competitors/history"),
    ]);
    if (summaryResult.status === "rejected" && eventsResult.status === "rejected") throw new Error("友商动态加载失败");
    setProfiles(profilesResult.status === "fulfilled" ? profilesResult.value.vendors || [] : []);
    setUpdated(profilesResult.status === "fulfilled" ? profilesResult.value.date || "" : "");
    setSummary(summaryResult.status === "fulfilled" ? summaryResult.value.vendors || {} : {});
    setV2(eventsResult.status === "fulfilled" ? eventsResult.value.items || [] : []);
    setBoard(boardResult.status === "fulfilled" ? boardResult.value : null);
    setHistory(historyResult.status === "fulfilled" ? historyResult.value : null);
    setError("");
  }, []);
  useEffect(() => { let active = true; void Promise.resolve().then(load).catch(reason => { if (active) setError(reason.message); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [load]);
  const all = useMemo(() => {
    const rows = Object.entries(summary).flatMap(([name, entries]) => entries.map(entry => ({ ...entry, vendor: aliases[entry.vendor || name] || entry.vendor || name })));
    const base = competitorItems(rows);
    const seen = new Set(base.map(item => `${item.owner}:${item.title}`));
    for (const event of v2) {
      const owner = aliases[event.vendor || ""] || event.vendor || "厂商待核实";
      if (seen.has(`${owner}:${event.title}`)) continue;
      seen.add(`${owner}:${event.title}`);
      base.push({ id: `event-${event.id}`, owner, title: event.title, summary: event.summary || "", category: event.categories?.[0] || event.event_type || "其他", topic: "其他", date: (event.published_at || event.first_seen_at || "").slice(0, 10), dateLabel: event.published_at ? "发布" : "发现", href: event.source_url || `/events/${event.id}`, detailHref: `/events/${event.id}`, priority: Object.values(event.scores || {}).some(score => score >= 80), scores: event.scores });
    }
    return base.sort((a, b) => b.date.localeCompare(a.date));
  }, [summary, v2]);
  const owners = [...new Set([...all.map(item => item.owner), ...profiles.map(profile => profile.name)])].filter(name => name !== "Huawei Cloud");
  const categories = [...new Set(all.map(item => item.category))].sort();
  const topics = [...new Set(all.map(item => item.topic))].sort();
  const scoped = all.filter(item => (!filters.owner || item.owner === filters.owner) && (!filters.days || daysAgo(item.date, filters.days)) && (!filters.query || `${item.title} ${item.summary} ${item.owner} ${vendorLabel(item.owner, false)} ${item.topic}`.toLowerCase().includes(filters.query.toLowerCase())));
  const visible = scoped.filter(item => (!filters.category || item.category === filters.category) && (!filters.topic || item.topic === filters.topic) && (!filters.onlyPriority || item.priority)).sort((a, b) => filters.sort === "priority" ? Number(b.priority) - Number(a.priority) || b.date.localeCompare(a.date) : b.date.localeCompare(a.date));
  const recent = all.filter(item => daysAgo(item.date, 7));
  const selectedVendor = filters.owner || owners.slice().sort((a, b) => all.filter(item => item.owner === b).length - all.filter(item => item.owner === a).length)[0];
  const selected = profiles.find(profile => profile.name === selectedVendor);
  const selectedItems = all.filter(item => item.owner === selectedVendor);
  const selectedTopics = distribution(selectedItems).slice(0, 5);
  const latestAnalysis = selectedItems.find(item => item.analysis)?.analysis;
  const sourceCounts = owners.map(name => ({ name, count: recent.filter(item => item.owner === name).length, points: history?.groups.find(group => aliases[group.name] === name || group.name === name)?.points })).sort((a, b) => b.count - a.count);
  async function refresh() { setRefreshing(true); try { const response = await authenticatedFetch(`${API}/api/competitors/refresh`, { method: "POST" }); if (!response.ok) throw new Error("刷新失败，请检查登录状态"); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "刷新失败"); } finally { setRefreshing(false); } }
  async function retry() { setLoading(true); try { await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "加载失败"); } finally { setLoading(false); } }
  const setFilter = (value: FilterState) => { setFilters(value); setLimit(24); };
  const selectOwner = (name: string) => setFilter({ ...filters, owner: filters.owner === name ? "" : name });
  const selectTopic = (name: string) => setFilter({ ...filters, topic: filters.topic === name ? "" : name });

  return <main className="insight-dashboard">
    <InsightPageHeader title={en ? "Competitor Insights" : "友商洞察"} description={en ? "Track product, capability and market moves from major cloud vendors." : "聚合主流厂商产品、能力与市场动作，帮助快速识别竞争重点与机会。"} count={all.length} updated={updated || board?.date || ""} refreshing={refreshing} refresh={() => void refresh()} canRefresh={!!user} />
    {error && <InsightErrorState text={error} retry={() => void retry()} />}
    {loading ? <InsightLoadingState /> : <>
      <div className="dash-top"><InsightHero title="近 7 天核心情报" board={board} metrics={[{ label: "监测厂商", value: owners.length }, { label: "近 7 天动态", value: recent.length }, { label: "重点动态", value: recent.filter(item => item.priority).length, note: "发布与价格变化等" }, { label: "重点方向", value: distribution(recent).filter(item => item.name !== "其他").length, note: "按现有文本归类" }]} /><InsightTrendChart title="友商动态趋势" history={history} days={trendDays} setDays={setTrendDays} /></div>
      <InsightSection title="友商概览" meta={`${owners.length} 家厂商`}><div className="dash-sources">{sourceCounts.map(item => <InsightSourceCard key={item.name} name={vendorLabel(item.name, en)} count={item.count} points={item.points} active={filters.owner === item.name} onClick={() => selectOwner(item.name)} unit="条近 7 天动态" />)}</div>{!owners.length && <InsightEmptyState text="当前没有可展示的厂商动态。" />}</InsightSection>
      <section className="dash-profile"><div className="dash-profile-head"><h2>选择观察厂商</h2>{owners.map(name => <button type="button" key={name} aria-pressed={selectedVendor === name} onClick={() => setFilter({ ...filters, owner: name })}>{vendorLabel(name, en)}</button>)}</div>{selectedVendor ? <div className="dash-profile-body"><div><h3>厂商定位</h3><p>{vendorLabel(selectedVendor, en)} · {selected?.region || "区域待核实"}</p><p>当前收录 {selectedItems.length} 条动态。</p></div><div><h3>核心优势</h3>{selected?.strengths?.length ? <ul>{selected.strengths.slice(0, 4).map(item => <li key={item}>{item}</li>)}</ul> : <p>暂无已登记的厂商画像。</p>}</div><div><h3>重点关注板块</h3><div className="dash-profile-tags">{selectedTopics.map(item => <span key={item.name}>{item.name} · {item.value}</span>)}</div>{!selectedTopics.length && <p>暂无可分类动态。</p>}</div><div><h3>相关产品 / 平台</h3><div className="dash-profile-tags">{selected?.products?.map(item => <span key={item}>{item}</span>)}</div>{!selected?.products?.length && <p>暂无已登记产品。</p>}</div><div><h3>竞争态势与洞察</h3><p className="dash-profile-brief">{latestAnalysis || selected?.vs_huawei || "暂无可核实的竞争分析。"}</p>{selected?.weaknesses?.length ? <details><summary>关注短板</summary><ul>{selected.weaknesses.map(item => <li key={item}>{item}</li>)}</ul></details> : null}</div></div> : <InsightEmptyState text="请选择一家具备真实数据的厂商。" />}</section>
      <div className="dash-content"><div className="dash-main"><InsightSection title="全部友商动态" meta={`${visible.length} 条匹配情报`}><InsightFilterBar value={filters} setValue={setFilter} owners={owners} categories={categories} topics={topics} ownerLabel="厂商" hasHeat={false} priorityLabel="重点动态" /><InsightList items={visible} view={filters.view} showHeat={false} limit={limit} more={() => setLimit(limit + 24)} /></InsightSection></div><aside className="dash-side-stack"><InsightTopicDistribution title="动态主题分布" values={distribution(scoped)} active={filters.topic} select={selectTopic} /><InsightKeywordPanel title="本周高频关键词" values={keywords(recent)} select={word => setFilter({ ...filters, query: word })} /></aside></div>
    </>}
  </main>;
}
