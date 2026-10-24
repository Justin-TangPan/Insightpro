"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import { useParams } from "next/navigation";
import { API } from "@/lib/api";
import { eventImage } from "@/lib/vendor-image";
import { abilities, cleanCategory, industry, meaningfulChange, products, scenario, solutionValue } from "@/lib/solution-intelligence";
import type { Solution } from "@/lib/solution-intelligence";

type History = { events: { id: number; title: string; summary: string | null; last_seen_at: string; event_type: string }[]; evidence: { id: number; source_name: string; canonical_url: string }[] };
export default function SolutionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [items, setItems] = useState<Solution[]>([]);
  const [detail, setDetail] = useState<Solution | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/api/solutions/catalog`, { signal: controller.signal }).then(response => response.ok ? response.json() : Promise.reject()).then(data => setItems(data.items)).catch(() => { if (!controller.signal.aborted) setError("方案读取失败"); });
    return () => controller.abort();
  }, []);
  const item = items.find(row => String(row.id) === id);
  useEffect(() => {
    const solution = item;
    if (!solution) return;
    const controller = new AbortController();
    fetch(`${API}/api/solutions/catalog/${solution.id}`, { signal: controller.signal }).then(response => response.ok ? response.json() : null).then(data => { if (!controller.signal.aborted) setDetail(data); }).catch(() => null);
    void crypto.subtle.digest("SHA-256", new TextEncoder().encode(solution.url)).then(hash => {
      const key = `solution:${Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, "0")).join("")}`;
      return fetch(`${API}/api/v2/entities/${key}`, { signal: controller.signal });
    }).then(response => response?.ok ? response.json() : null).then(data => { if (!controller.signal.aborted) setHistory(data); }).catch(() => null);
    return () => controller.abort();
  }, [item]);
  const full: Solution | undefined = item && detail?.id === item.id ? { ...item, ...detail } : item;
  const related = useMemo(() => item ? items.filter(row => row.id !== item.id && scenario(row) === scenario(item)).sort((a, b) => Number(a.vendor !== item.vendor) - Number(b.vendor !== item.vendor)).slice(0, 6) : [], [item, items]);
  if (error) return <main className="solution-page"><div className="solution-alert" role="alert">{error}</div></main>;
  if (!full) return <main className="solution-page"><div className="solution-empty">正在读取方案详情…</div></main>;
  return <main className="solution-page solution-detail"><Link className="solution-back" href="/insights/solutions"><ArrowLeft size={16}/> 返回解决方案</Link><section className="solution-hero"><div><span className="solution-kicker">SOLUTION PROFILE / {full.vendor}</span><h1>{full.title}</h1><p>{solutionValue(full)}</p></div><div className="solution-hero-side"><span className="solution-live"><i/>官方方案已收录</span><small>最近变化 · {full.last_changed_date || "—"}</small></div></section><div className="solution-detail-grid"><div><section className="solution-section"><header className="solution-head"><div><h2>方案基本信息</h2></div></header><div className="solution-detail-facts"><div><span>厂商</span><strong>{full.vendor}</strong></div><div><span>场景</span><strong>{scenario(full)}</strong></div><div><span>行业</span><strong>{industry(full)}</strong></div><div><span>原始分类</span><strong>{cleanCategory(full.category) || "其他"}</strong></div><div><span>首次收录</span><strong>{full.first_seen_date || "—"}</strong></div></div></section><section className="solution-section"><header className="solution-head"><div><h2>解决什么问题</h2></div></header><p className="solution-detail-copy">{solutionValue(full)}</p><h3>方案架构与实施</h3><p className="solution-detail-copy">{full.detail_text ? full.detail_text.slice(0, 1200) : "官方来源未提供可验证的架构详情。"}</p><h3>核心产品与技术能力</h3><p className="solution-detail-copy">相关产品：{products(full)}</p><div className="solution-tags">{abilities(full).length ? abilities(full).map(value => <span key={value}>{value}</span>) : <span>官方资料未明确标注技术能力</span>}</div><p className="solution-detail-note">具体架构、部署方式与产品清单以官方方案页面为准。</p></section><section className="solution-section"><header className="solution-head"><div><h2>最近变化与时间线</h2></div></header><div className="solution-timeline"><div><time>{full.last_changed_date || "—"}</time><strong>{full.title}</strong><p>{meaningfulChange(full.change_summary) ? full.change_summary : "已检查官方方案页面；暂无可核实的具体变更说明。"}</p>{full.event_id && <Link href={`/events/${full.event_id}`}>查看事件证据 <ArrowUpRight size={14}/></Link>}</div>{history?.events.filter(row => row.id !== full.event_id).map(row => <div key={row.id}><time>{row.last_seen_at?.slice(0, 10)}</time><strong>{row.title}</strong><p>{row.summary}</p><Link href={`/events/${row.id}`}>查看事件 <ArrowUpRight size={14}/></Link></div>)}</div></section></div><aside><div className="solution-detail-visual"><Image src={eventImage(full.image_url, full.vendor)} alt={full.image_url ? full.title : full.vendor} width={280} height={145} unoptimized /></div><section className="solution-section"><header className="solution-head"><div><h2>同场景方案</h2></div></header><div className="solution-related">{related.map(row => <Link key={row.id} href={`/insights/solutions/${row.id}`}><small>{row.vendor} · {row.last_changed_date}</small><strong>{row.title}</strong><span>{abilities(row).slice(0, 3).join(" / ") || scenario(row)}</span></Link>)}</div></section><section className="solution-section"><header className="solution-head"><div><h2>官方来源</h2></div></header><a className="solution-source" href={full.url} target="_blank" rel="noopener noreferrer">查看官方解决方案 <ArrowUpRight size={15}/></a>{history?.evidence.map(row => <a className="solution-source" key={row.id} href={row.canonical_url} target="_blank" rel="noopener noreferrer">{row.source_name} <ArrowUpRight size={15}/></a>)}</section></aside></div></main>;
}
