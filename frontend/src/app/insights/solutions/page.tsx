"use client";

import Link from "next/link";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, ArrowUpRight, RefreshCw, Search } from "lucide-react";
import { API } from "@/lib/api";
import { eventImage } from "@/lib/vendor-image";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { usePreferences } from "@/lib/preferences";
import { abilities, categoryNoise, cleanCategory, dateInPeriod, eventType, industry, meaningfulChange, periods, priority, products, scenario, solutionValue } from "@/lib/solution-intelligence";
import type { Period, Solution, SolutionEvent } from "@/lib/solution-intelligence";

type Catalog = { items: Solution[]; removed_items?: Solution[]; count: number; last_checked: string | null; daily_insight: { new: number; updated: number; removed: number } };
type Board = { summary?: { judgment?: string; focus?: { event_id?: number; title?: string; why?: string } }; date?: string };
const vendorName = (value: string, en: boolean) => en ? value : ({ "Alibaba Cloud": "阿里云", "Huawei Cloud": "华为云" }[value] || value);
const readable = (value: string, length = 115) => value.length > length ? `${value.slice(0, length).trimEnd()}…` : value;
const dateText = (value?: string | null) => value ? value.slice(0, 10) : "—";
const searchText = (item: Solution) => `${item.title} ${item.vendor} ${vendorName(item.vendor, false)} ${item.category} ${scenario(item)} ${abilities(item).join(" ")} ${item.source_description} ${item.summary}`.toLowerCase();

export default function SolutionInsightsPage() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [events, setEvents] = useState<SolutionEvent[]>([]);
  const [board, setBoard] = useState<Board | null>(null);
  const [period, setPeriod] = useState<Period>("7days");
  const [vendor, setVendor] = useState("");
  const [query, setQuery] = useState("");
  const [scene, setScene] = useState("");
  const [eventFilter, setEventFilter] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [catalogResult, boardResult, eventResult] = await Promise.all([
        fetch(`${API}/api/solutions/catalog`),
        fetch(`${API}/api/boards/solutions/daily-insight`),
        fetch(`${API}/api/v2/events?business_scope=solutions&limit=100`),
      ]);
      if (!catalogResult.ok) throw new Error(`方案目录读取失败 (${catalogResult.status})`);
      setCatalog(await catalogResult.json());
      setBoard(boardResult.ok ? await boardResult.json() : null);
      setEvents(eventResult.ok ? (await eventResult.json()).items : []);
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "解决方案数据读取失败"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const refresh = async () => {
    setRefreshing(true);
    try {
      const response = await authenticatedFetch(`${API}/api/solutions/catalog/refresh`, { method: "POST" });
      if (!response.ok) throw new Error(response.status === 401 ? "请先登录再手动检查更新" : `检查更新失败 (${response.status})`);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "检查更新失败"); }
    finally { setRefreshing(false); }
  };

  const all = useMemo(() => catalog?.items || [], [catalog]);
  const vendors = useMemo(() => [...new Set(all.map(item => item.vendor))], [all]);
  const normalizedQuery = query.trim().toLowerCase();
  const scope = useMemo(() => all.filter(item => (!vendor || item.vendor === vendor) && (!normalizedQuery || searchText(item).includes(normalizedQuery))), [all, vendor, normalizedQuery]);
  const removed = (catalog?.removed_items || []).filter(item => (!vendor || item.vendor === vendor) && (!normalizedQuery || searchText(item).includes(normalizedQuery)) && dateInPeriod(item.last_changed_date, period));
  const timed = useMemo(() => scope.filter(item => !item.is_baseline && !categoryNoise(item.change_summary) && dateInPeriod(item.last_changed_date, period)), [scope, period]);
  const recent = useMemo(() => timed.sort((a, b) => priority(b) - priority(a) || b.last_changed_date.localeCompare(a.last_changed_date)), [timed]);
  const namedEvents = useMemo(() => events.filter(item => (!vendor || item.vendor === vendor) && dateInPeriod(item.published_at || item.first_seen_at, period) && !categoryNoise(item.summary || "") && (!normalizedQuery || `${item.title} ${item.summary} ${item.vendor}`.toLowerCase().includes(normalizedQuery))), [events, vendor, period, normalizedQuery]);
  const directory = useMemo(() => scope.filter(item => !scene || scenario(item) === scene), [scope, scene]);
  const scenes = useMemo(() => {
    const map = new Map<string, { count: number; updates: number; vendors: Set<string> }>();
    for (const item of scope) {
      const name = scenario(item);
      const row = map.get(name) || { count: 0, updates: 0, vendors: new Set<string>() };
      row.count++; row.vendors.add(item.vendor);
      if (dateInPeriod(item.last_changed_date, period) && !item.is_baseline) row.updates++;
      map.set(name, row);
    }
    return [...map].sort((a, b) => b[1].updates - a[1].updates || b[1].count - a[1].count);
  }, [scope, period]);
  const capabilities = useMemo(() => {
    const map = new Map<string, { count: number; updates: number }>();
    for (const item of scope) for (const ability of abilities(item)) {
      const row = map.get(ability) || { count: 0, updates: 0 };
      row.count++;
      if (dateInPeriod(item.last_changed_date, period) && !item.is_baseline) row.updates++;
      map.set(ability, row);
    }
    return [...map].sort((a, b) => b[1].updates - a[1].updates || b[1].count - a[1].count).slice(0, 9);
  }, [scope, period]);
  const vendorRows = vendors.filter(name => !vendor || vendor === name).map(name => {
    const items = scope.filter(item => item.vendor === name);
    const changes = timed.filter(item => item.vendor === name);
    const active = [...new Set(changes.map(scenario))].slice(0, 4);
    return { name, total: items.length, updates: changes.length, added: changes.filter(item => eventType(item) === "新方案").length, active, latest: changes[0]?.last_changed_date || items[0]?.last_seen_date };
  });
  const focus = recent[0];
  const topVendor = [...vendorRows].sort((a, b) => b.updates - a.updates)[0];
  const topScene = scenes.find(([, row]) => row.updates > 0);
  const topAbility = capabilities.find(([, row]) => row.updates > 0);
  const judgment = !vendor && !normalizedQuery && period === "7days" && recent.some(item => item.event_id === board?.summary?.focus?.event_id) && board?.summary?.judgment ? board.summary.judgment :
    topVendor?.updates ? `${vendorName(topVendor.name, en)}在${periods.find(item => item.key === period)?.label}有 ${topVendor.updates} 项方案发生变化，${topScene?.[0] || "多个场景"}是当前最活跃的方向。` : "当前范围内暂无可核实的方案变化。";
  const eventTypes = ["新方案", "方案更新", "能力新增", "架构调整", "场景扩展", "产品调整", "方案下线"];
  const updates = [...recent, ...removed].filter(item => !eventFilter || eventType(item) === eventFilter).sort((a, b) => b.last_changed_date.localeCompare(a.last_changed_date));
  const shown = directory.slice((page - 1) * 12, page * 12);
  const selectVendor = (value: string) => { setVendor(value); setScene(""); setPage(1); };
  const chooseScene = (value: string) => { setScene(value); setPage(1); document.getElementById("solution-directory")?.scrollIntoView({ behavior: "smooth" }); };

  return <main className="solution-page">
    <section className="solution-hero"><div><span className="solution-kicker">INSIGHTPRO / SOLUTION INTELLIGENCE</span><h1>{en ? "Solutions" : "解决方案"}</h1><p>{en ? "Track vendor solution changes, scenario investment and technical capabilities." : "跟踪主流云厂商与 AI 厂商解决方案变化，识别场景布局、能力演进与竞争方向。"}</p></div><div className="solution-hero-side"><label>时间范围<select value={period} onChange={event => setPeriod(event.target.value as Period)}>{periods.map(item => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label><small>最近更新 · {dateText(catalog?.last_checked)}</small><span className="solution-live"><i />{error ? "数据读取失败" : refreshing ? "更新中" : "数据已就绪"}</span></div></section>
    <section className="solution-metrics" aria-label="核心指标">{[
      ["已收录解决方案", scope.length, "官方方案目录"], ["周期内方案变化", timed.length + removed.length, periods.find(item => item.key === period)?.label || ""],
      ["重点厂商", vendorRows.length, "当前筛选范围"], ["活跃场景", scenes.filter(([, row]) => row.updates > 0).length, "周期内有变化"],
    ].map(([label, value, hint]) => <article key={label}><span>{label}</span><strong>{loading ? "—" : value}</strong><small>{hint}</small></article>)}</section>
    <div className="solution-status-summary"><span>新增 <b>{timed.filter(item => eventType(item) === "新方案").length}</b></span><span>更新 <b>{timed.filter(item => eventType(item) !== "新方案").length}</b></span><span>下线 <b>{removed.length}</b></span><small>当前筛选周期 · 来自官方目录变更</small></div>
    <div className="solution-toolbar"><div className="solution-periods" role="group" aria-label="时间筛选">{periods.map(item => <button key={item.key} type="button" aria-pressed={period === item.key} onClick={() => setPeriod(item.key)}>{item.label}</button>)}</div><label className="solution-search"><Search size={17}/><span className="sr-only">搜索厂商、方案、场景、能力与产品</span><input value={query} onChange={event => { setQuery(event.target.value); setPage(1); }} placeholder="搜索厂商、方案、场景、能力与产品" /></label><button type="button" className="solution-refresh" disabled={refreshing} onClick={refresh}><RefreshCw size={15} className={refreshing ? "animate-spin" : ""}/>{refreshing ? "对比中" : "刷新"}</button></div>
    <nav className="solution-vendor-tabs" aria-label="厂商筛选"><button type="button" aria-pressed={!vendor} onClick={() => selectVendor("")}>全部厂商</button>{vendors.map(name => <button key={name} type="button" aria-pressed={vendor === name} onClick={() => selectVendor(name)}>{vendorName(name, en)}</button>)}</nav>
    {error && <div className="solution-alert" role="alert">{error}<button onClick={load} type="button">重试</button></div>}
    {loading ? <div className="solution-empty" role="status">正在读取解决方案情报…</div> : <>
      <section className="solution-section"><header className="solution-head"><div><span className="solution-kicker">PERIOD ASSESSMENT</span><h2>本期解决方案判断 · {periods.find(item => item.key === period)?.label}</h2><p>依据当前筛选范围内的官方方案变化归纳</p></div></header><div className="solution-judgment"><div className="solution-overall"><span>总体判断</span><p>{judgment}</p><small>{timed.length} 条周期内方案变化 · {namedEvents.length} 条事件记录</small></div><div className="solution-judgment-cards">{[
        ["厂商动作", topVendor?.updates ? `${vendorName(topVendor.name, en)}有 ${topVendor.updates} 项方案发生变化，覆盖 ${topVendor.active.join("、") || "多个场景"}。` : "当前周期暂无厂商变化。"],
        ["场景变化", topScene ? `${topScene[0]}有 ${topScene[1].updates} 项方案发生变化，覆盖 ${topScene[1].vendors.size} 家厂商。` : "当前周期暂无活跃场景。"],
        ["能力变化", topAbility ? `${topAbility[0]}出现在 ${topAbility[1].count} 项方案中，其中 ${topAbility[1].updates} 项在本周期变化。` : "当前周期暂无可识别的能力变化。"],
      ].map(([label, text]) => <article key={label}><span>{label}</span><strong>{text}</strong></article>)}</div></div></section>
      <section className="solution-section"><header className="solution-head"><div><span className="solution-kicker">KEY CHANGES</span><h2>重点方案变化</h2><p>优先展示有具体变化描述、相关技术能力及近期更新的官方方案</p></div><a href="#solution-latest">查看全部 <ArrowRight size={15}/></a></header>{focus ? <div className="solution-feature"><article className="solution-feature-main"><div className="solution-feature-brand"><Image src={eventImage(focus.image_url, focus.vendor)} alt={focus.image_url ? focus.title : vendorName(focus.vendor, en)} width={240} height={160} unoptimized /></div><div className="solution-feature-body"><span className="solution-tag">{vendorName(focus.vendor, en)} · {scenario(focus)}</span><time>{dateText(focus.last_changed_date)}</time><h3>{focus.title}</h3><p>{readable(meaningfulChange(focus.change_summary) ? focus.change_summary : solutionValue(focus), 180)}</p><div className="solution-feature-reason"><strong>为什么值得关注</strong><span>{board?.summary?.focus?.event_id === focus.event_id && !vendor && !normalizedQuery && period === "7days" ? readable(board?.summary?.focus?.why || "", 130) : `${scenario(focus)}方向的方案变化；${abilities(focus).slice(0, 3).join("、") || "具体能力"}可从官方来源继续核实。`}</span></div><div className="solution-feature-bottom"><span>{eventType(focus)} · {abilities(focus).slice(0, 3).join(" / ") || cleanCategory(focus.category)}</span><Link href={`/insights/solutions/${focus.id}`}>查看详情 <ArrowRight size={15}/></Link></div></div></article><div className="solution-feature-list">{recent.slice(1, 6).map((item, index) => <Link href={`/insights/solutions/${item.id}`} key={item.id}><b>{String(index + 2).padStart(2, "0")}</b><span><small>{vendorName(item.vendor, en)} · {scenario(item)} · {dateText(item.last_changed_date)}</small><strong>{item.title}</strong></span><em>{eventType(item)}</em></Link>)}</div></div> : <div className="solution-empty">当前周期暂无可核实的方案变化。</div>}</section>
      <section className="solution-section"><header className="solution-head"><div><span className="solution-kicker">VENDOR WATCH</span><h2>厂商动态</h2><p>各厂商的方案覆盖、近期变化与活跃场景</p></div></header><div className="solution-vendor-grid">{vendorRows.map(row => <button key={row.name} type="button" onClick={() => selectVendor(row.name)} aria-pressed={vendor === row.name}><Image src={row.name === "Huawei Cloud" ? "/brand-logos/huawei.svg" : "/brand-logos/alibabacloud.svg"} alt="" width={50} height={50} unoptimized/><strong>{vendorName(row.name, en)}</strong><span><b>{row.total}</b> 个方案 <b>{row.updates}</b> 次变化 <b>{row.added}</b> 个新增</span><small>活跃场景：{row.active.join(" / ") || "本周期暂无变化"}</small><time>最近更新 {dateText(row.latest)}</time></button>)}</div></section>
      <section className="solution-section"><header className="solution-head"><div><span className="solution-kicker">SCENARIO & CAPABILITY</span><h2>场景与能力趋势</h2><p>从已收录方案与当前周期变化中聚合；“升温”表示本周期有变化</p></div></header><div className="solution-trends"><div><h3>场景趋势</h3><div className="solution-table-wrap"><table><thead><tr><th>场景</th><th>方案</th><th>变化</th><th>厂商</th><th>状态</th></tr></thead><tbody>{scenes.slice(0, 10).map(([name, row]) => <tr key={name}><td><button type="button" onClick={() => chooseScene(name)}>{name}</button></td><td>{row.count}</td><td>{row.updates}</td><td>{row.vendors.size}</td><td><span className={row.updates ? "solution-status hot" : "solution-status"}>{row.updates ? "活跃" : "稳定"}</span></td></tr>)}</tbody></table></div></div><div><h3>能力趋势</h3><div className="solution-ability-list">{capabilities.map(([name, row]) => <div key={name}><span>{name}</span><div className="solution-track"><i style={{ width: `${Math.max(5, row.count / (capabilities[0]?.[1].count || 1) * 100)}%` }}/></div><strong>{row.count} 项</strong><small>{row.updates} 项变化</small></div>)}</div></div></div></section>
      <section className="solution-section" id="solution-directory"><header className="solution-head"><div><span className="solution-kicker">SOLUTION CATALOG</span><h2>解决方案目录</h2><p>完整目录始终可浏览；时间仅影响每条方案的变化状态</p></div><span>{directory.length} 个方案</span></header><div className="solution-scene-tabs" role="group" aria-label="场景筛选"><button type="button" aria-pressed={!scene} onClick={() => { setScene(""); setPage(1); }}>全部场景</button>{scenes.slice(0, 12).map(([name]) => <button type="button" key={name} aria-pressed={scene === name} onClick={() => { setScene(name); setPage(1); }}>{name}</button>)}</div>{scene && <div className="solution-compare"><strong>{scene} · 同场景方案比较</strong><p>当前范围涉及 {[...new Set(directory.map(item => vendorName(item.vendor, en)))].join("、")}，点击方案查看各厂商的产品、能力、部署信息和官方来源。</p></div>}{scene && directory.length > 0 && <div className="solution-table-wrap"><table className="solution-updates-table"><thead><tr><th>厂商</th><th>同场景方案</th><th>核心产品</th><th>核心能力</th><th>部署方式</th><th>最近更新</th></tr></thead><tbody>{[...directory].sort((a, b) => a.vendor.localeCompare(b.vendor)).slice(0, 12).map(item => <tr key={item.id}><td>{vendorName(item.vendor, en)}</td><td><Link href={`/insights/solutions/${item.id}`}>{item.title}</Link></td><td>{readable(products(item), 45)}</td><td>{abilities(item).slice(0, 4).join(" / ") || "官方资料未明确"}</td><td>{/私有化|私有部署|on.premise/i.test(item.source_description) ? "私有化" : /一键部署|云上部署/i.test(item.source_description) ? "云上部署" : "以官方资料为准"}</td><td>{dateText(item.last_changed_date)}</td></tr>)}</tbody></table></div>}<div className="solution-directory">{shown.map(item => <article key={item.id}><div className="solution-directory-top"><span>{vendorName(item.vendor, en)}</span><span className={dateInPeriod(item.last_changed_date, period) && !item.is_baseline ? "solution-status hot" : "solution-status"}>{dateInPeriod(item.last_changed_date, period) && !item.is_baseline ? eventType(item) : "已收录"}</span></div><h3><Link href={`/insights/solutions/${item.id}`}>{item.title}</Link></h3><p>{readable(solutionValue(item), 90)}</p><div className="solution-tags"><span>{scenario(item)}</span><span>行业：{industry(item)}</span>{abilities(item).slice(0, 3).map(value => <span key={value}>{value}</span>)}</div><small className="solution-product-line">相关产品：{readable(products(item), 32)}</small><footer><time>更新 {dateText(item.last_changed_date || item.last_seen_date)}</time><Link href={`/insights/solutions/${item.id}`}>查看方案 <ArrowUpRight size={14}/></Link></footer></article>)}</div>{!directory.length && <div className="solution-empty">没有匹配的方案。</div>}{directory.length > 12 && <div className="solution-pagination"><button type="button" disabled={page === 1} onClick={() => setPage(value => value - 1)}>上一页</button><span>{page} / {Math.ceil(directory.length / 12)}</span><button type="button" disabled={page * 12 >= directory.length} onClick={() => setPage(value => value + 1)}>下一页</button></div>}</section>
      <section className="solution-section" id="solution-latest"><header className="solution-head"><div><span className="solution-kicker">LATEST UPDATES</span><h2>最新方案动态</h2><p>按时间查看官方方案变化与来源</p></div><span>{updates.length} 条</span></header><div className="solution-scene-tabs" role="group" aria-label="事件类型筛选"><button type="button" aria-pressed={!eventFilter} onClick={() => setEventFilter("")}>全部</button>{eventTypes.map(type => <button key={type} type="button" aria-pressed={eventFilter === type} onClick={() => setEventFilter(type)}>{type}</button>)}</div><div className="solution-table-wrap"><table className="solution-updates-table"><thead><tr><th>时间</th><th>厂商</th><th>解决方案</th><th>场景</th><th>事件类型</th><th>变化摘要</th><th>来源</th></tr></thead><tbody>{updates.slice(0, 30).map(item => <tr key={item.id}><td>{dateText(item.last_changed_date)}</td><td>{vendorName(item.vendor, en)}</td><td><Link href={item.is_active === false ? item.url : `/insights/solutions/${item.id}`}>{item.title}</Link></td><td>{scenario(item)}</td><td><span className="solution-status hot">{eventType(item)}</span></td><td title={item.change_summary}>{readable(meaningfulChange(item.change_summary) ? item.change_summary : solutionValue(item), 72)}</td><td><a href={item.url} target="_blank" rel="noopener noreferrer">官方页面 <ArrowUpRight size={13}/></a></td></tr>)}</tbody></table></div>{!updates.length && <div className="solution-empty">当前筛选范围暂无方案动态。</div>}</section>
    </>}
  </main>;
}
