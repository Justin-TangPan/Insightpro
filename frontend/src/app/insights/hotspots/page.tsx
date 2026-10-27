"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Code2, Filter, Search, Sparkles } from "lucide-react";
import { HotspotTrendingGrid } from "./_components/hotspot-trending-grid";
import { HotspotEvaluationPanel } from "./_components/hotspot-evaluation-panel";
import { HotspotHistoryPanel, HistoryDateIndicator } from "./_components/hotspot-history-panel";
import { HotspotFilters } from "./_components/hotspot-filters";
import { historySeries, metric, projectCategories, projectCategory, sparkline } from "./_components/ecosystem-data";
import { useHotspotData } from "./_components/use-hotspot-data";
import { usePreferences } from "@/lib/preferences";
import { DailyBoardInsight } from "@/components/daily-board-insight";
import { InsightPageShell } from "@/components/insight-page-shell";

export default function HotspotsPage() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [showCategories, setShowCategories] = useState(false);
  const {
    period, date, loading, error, refreshing, showHistory, historyLoading, historyDate,
    evalLoading, evalRefreshing, evalError, savingRepo, savedRepos, saveError,
    displayData, displayEvaluations, history,
    setPeriod, setHistoryDate, setShowHistory, handleRefresh, handleReload, handleEvalRefresh, savePractice,
  } = useHotspotData();
  const filtered = useMemo(() => displayData.filter(item => {
    const matchesQuery = `${item.repo_name} ${item.description} ${item.language} ${(item.topics || []).join(" ")}`.toLowerCase().includes(query.trim().toLowerCase());
    return matchesQuery && (category === "all" || projectCategory(item) === category);
  }), [displayData, query, category]);
  const prior = history.find(day => day.date < date)?.items || [];
  const newCount = prior.length ? displayData.filter(item => !prior.some(previous => previous.repo_url === item.repo_url)).length : null;
  const contributors = displayData.reduce((total, item) => total + (Number(item.contributors_count) || 0), 0);
  const hasContributors = displayData.some(item => item.contributors_count != null);
  const trends = projectCategories.slice(1, -1).map(group => {
    const items = displayData.filter(item => projectCategory(item) === group.key);
    const growth = items.reduce((total, item) => total + metric(item.today_stars), 0);
    const series = historySeries(history, item => projectCategory(item) === group.key);
    return { ...group, items, growth, points: sparkline(series) };
  }).filter(group => group.items.length).sort((a, b) => b.growth - a.growth).slice(0, 4);
  const growthLabel = period === "daily" ? (en ? "today" : "今日") : period === "weekly" ? (en ? "this week" : "本周") : period === "monthly" ? (en ? "this month" : "本月") : (en ? "in this view" : "当前视图");
  const updated = date ? new Date(`${date}T00:00:00`).toLocaleDateString(en ? "en-US" : "zh-CN") : (en ? "Awaiting data" : "等待数据");

  return <InsightPageShell artwork="/illustrations/tech-ecosystem.png" title={en ? "Technology Ecosystem" : "技术生态"} description={en ? "Track AI projects, open source ecosystems and developer activity to spot emerging technology." : "跟踪全球 AI 技术项目、开源生态与开发者动态，洞察技术演进方向。"} icon={<Code2 size={22} />} range={`${en ? "Current range" : "时间范围"} · ${period === "daily" ? (en ? "Today" : "今日") : period === "weekly" ? (en ? "This week" : "本周") : period === "monthly" ? (en ? "This month" : "本月") : (en ? "All" : "全部")}`} updated={updated} status={refreshing ? (en ? "Updating" : "更新中") : error ? (en ? "Load failed" : "加载失败") : (en ? "Data ready" : "数据已就绪")} metrics={[{ label: en ? "Projects in view" : "当前项目", value: loading ? "—" : displayData.length.toLocaleString() }, { label: en ? "New vs previous capture" : "较上次新增", value: newCount == null || loading ? "—" : newCount.toLocaleString() }, { label: en ? "Active topics" : "活跃趋势", value: loading ? "—" : trends.length }, { label: en ? "Reported contributors" : "已披露贡献者", value: loading || !hasContributors ? "—" : contributors.toLocaleString() }]}>
    <div className="ecosystem-page">

    <div className="ecosystem-toolbar"><HotspotFilters period={period} onPeriodChange={p => { setPeriod(p); setHistoryDate(""); }} showHistory={showHistory} onToggleHistory={() => setShowHistory(!showHistory)} refreshing={refreshing} onRefresh={handleRefresh}><label className="ecosystem-search"><Search size={16} /><span className="sr-only">{en ? "Search projects" : "搜索项目"}</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder={en ? "Search projects and technologies" : "搜索项目、技术关键词..."} /></label><button type="button" className="ecosystem-filter-button" aria-expanded={showCategories} onClick={() => setShowCategories(!showCategories)}><Filter size={15} />{en ? "Filter" : "筛选"}{category !== "all" && <i />}</button></HotspotFilters></div>
    {showCategories && <div className="ecosystem-category-row" role="group" aria-label={en ? "Project category" : "项目分类"}>{projectCategories.map(item => <button key={item.key} type="button" aria-pressed={category === item.key} onClick={() => setCategory(item.key)}>{en ? item.en : item.label}</button>)}</div>}
    {error && <div role="alert" className="ecosystem-alert">{en ? "Trending projects could not be loaded." : "热门项目加载失败。"} <button type="button" onClick={() => void handleReload()}>{en ? "Retry" : "重试"}</button></div>}
    {showHistory && <HotspotHistoryPanel history={history} historyLoading={historyLoading} historyDate={historyDate} onDateSelect={setHistoryDate} />}
    <HistoryDateIndicator historyDate={historyDate} />
    {saveError && <div role="alert" className="ecosystem-alert">{saveError}</div>}

    <section className="ecosystem-section" id="ecosystem-hot"><div className="ecosystem-section-head"><div><h2>{en ? "Popular projects · last 7 days" : "近期热门项目 · 近 7 天"}</h2><p>{en ? "Ranked by the selected GitHub Trending view" : "基于所选 GitHub Trending 周期与项目增长数据"}</p></div><a href="#ecosystem-more">{en ? "View all" : "查看全部"}<ArrowRight size={15} /></a></div><HotspotTrendingGrid loading={loading} displayData={filtered} history={history} savingRepo={savingRepo} savedRepos={savedRepos} onSave={savePractice} /></section>

    <section className="ecosystem-section" id="ecosystem-trends"><div className="ecosystem-section-head"><div><h2>{en ? "Technology trends and signals" : "技术趋势与热点"}</h2><p>{en ? "Grouped from live project names, descriptions and topics" : "从当前项目描述与技术标签归纳，按今日增星排序"}</p></div></div>{trends.length ? <div className="trend-grid">{trends.map(trend => <article className="ecosystem-card trend-card" key={trend.key}><span className={`trend-icon trend-${trend.key}`}><Sparkles size={19} /></span><span className="trend-kind">{en ? trend.en : trend.label}</span><h3>{en ? `${trend.en} projects are drawing attention` : `${trend.label}项目持续活跃`}</h3><p>{en ? `${trend.items.length} projects in the current view, with ${trend.growth.toLocaleString()} stars gained ${growthLabel}.` : `当前视图收录 ${trend.items.length} 个相关项目，${growthLabel}累计增星 ${trend.growth.toLocaleString()}。`}</p><div className="trend-footer"><strong>+{trend.growth.toLocaleString()} <small>{en ? `stars ${growthLabel}` : `${growthLabel} Stars`}</small></strong>{trend.points ? <svg viewBox="0 0 100 34" preserveAspectRatio="none" aria-label={en ? "Observed trend" : "历史增长趋势"}><polyline points={trend.points} /></svg> : <span>{en ? "No history" : "暂无历史"}</span>}</div></article>)}</div> : <div className="ecosystem-empty">{en ? "Trend signals will appear when projects are available" : "有项目数据后显示趋势信号"}</div>}<DailyBoardInsight board="github" compact /></section>

    <HotspotEvaluationPanel historyDate={historyDate} evalLoading={evalLoading} evalRefreshing={evalRefreshing} evalError={evalError} displayEvaluations={displayEvaluations} displayData={displayData} onEvalRefresh={handleEvalRefresh} />

    <section className="ecosystem-section" id="ecosystem-more"><div className="ecosystem-section-head"><div><h2>{en ? "More projects" : "更多项目"}</h2><p>{en ? `${filtered.length} projects · compact view` : `共 ${filtered.length} 个项目 · 快速浏览`}</p></div><a href="https://github.com/trending" target="_blank" rel="noopener noreferrer">GitHub Trending <ArrowRight size={15} /></a></div><div className="ecosystem-tabs" role="group" aria-label={en ? "Project category" : "项目分类"}>{projectCategories.map(item => <button type="button" key={item.key} aria-pressed={category === item.key} onClick={() => setCategory(item.key)}>{en ? item.en : item.label}</button>)}</div><div className="ecosystem-table-wrap"><table className="ecosystem-table"><thead><tr><th>#</th><th>{en ? "Project" : "项目名称"}</th><th>{en ? "Description" : "简介"}</th><th>{en ? "Language" : "语言"}</th><th>Stars</th><th>{en ? `Growth ${growthLabel}` : `${growthLabel}增长`}</th><th>{en ? "Updated" : "更新时间"}</th><th>{en ? "Action" : "操作"}</th></tr></thead><tbody>{filtered.map((item, index) => <tr key={item.repo_url || index}><td>{index + 1}</td><td className="table-name">{item.repo_name}</td><td className="table-description" title={item.description}>{item.description || "—"}</td><td>{item.language || "—"}</td><td>{metric(item.stars).toLocaleString()}</td><td className="table-growth">+{metric(item.today_stars).toLocaleString()}</td><td>{item.pushed_at ? new Date(item.pushed_at).toLocaleDateString(en ? "en-US" : "zh-CN") : date || "—"}</td><td>{item.entity_key ? <Link href={`/repositories/${encodeURIComponent(item.entity_key)}`} target="_blank" rel="noopener noreferrer">{en ? "View" : "查看"}</Link> : <a href={item.repo_url} target="_blank" rel="noopener noreferrer">{en ? "View" : "查看"}</a>}</td></tr>)}</tbody></table>{!filtered.length && <div className="ecosystem-empty">{en ? "No matching projects" : "暂无匹配项目"}</div>}</div></section>
    </div>
  </InsightPageShell>;
}
