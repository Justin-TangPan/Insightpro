import type { ReactNode } from "react";

type Metric = { label: string; value: string | number; note?: string };

export function InsightPageShell({ title, description, icon, artwork, range, updated, status, metrics, action, children }: {
  title: string;
  description: string;
  icon: ReactNode;
  artwork?: string;
  range: string;
  updated: string;
  status: string;
  metrics: Metric[];
  action?: ReactNode;
  children: ReactNode;
}) {
  return <main className="insight-page-shell">
    <header className="insight-page-hero">
      {artwork && <span className="insight-page-art" style={{ backgroundImage: `url(${artwork})` }} aria-hidden="true" />}
      <div className="insight-page-heading"><span className="insight-page-icon" aria-hidden="true">{icon}</span><div><h1>{title}</h1><p>{description}</p></div></div>
      <div className="insight-page-status"><span className="insight-range">{range}</span><span>更新于 {updated || "待核实"}</span><span role="status" className={`insight-data-state ${/失败|unavailable/i.test(status) ? "is-error" : ""}`}><i />{status}</span>{action}</div>
      <div className="insight-page-kpis" aria-label="核心指标">{metrics.slice(0, 4).map(item => <article key={item.label}><span>{item.label}</span><strong>{item.value}</strong>{item.note && <small>{item.note}</small>}</article>)}</div>
    </header>
    {children}
  </main>;
}
