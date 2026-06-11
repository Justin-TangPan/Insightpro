import { ReactNode } from "react";
import Link from "next/link";

interface InsightCardProps {
  children: ReactNode;
  className?: string;
  href?: string;
  gradient?: boolean;
  glass?: boolean;
}

export function InsightCard({ children, className = "", href, gradient = false, glass = false }: InsightCardProps) {
  const base = glass
    ? `glass rounded-2xl p-6 ${className}`
    : gradient
    ? `rounded-2xl bg-white border border-slate-200/60 p-6 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card-hover)] transition-all duration-300 ${className}`
    : `rounded-2xl bg-white border border-slate-200/60 p-6 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card-hover)] transition-all duration-300 ${className}`;

  if (href) {
    return (
      <Link href={href} className={`${base} block hover:-translate-y-0.5`}>
        {children}
      </Link>
    );
  }
  return <div className={base}>{children}</div>;
}

export function InsightCardHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-5 pb-4 border-b border-slate-100">
      <h3 className="font-serif text-xl font-bold text-ink">{title}</h3>
      {action}
    </div>
  );
}

export function StatCard({
  label,
  value,
  trend,
  icon: Icon,
  href,
  color = "primary",
}: {
  label: string;
  value: string;
  trend?: string;
  icon: React.ElementType;
  href?: string;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    primary: "from-indigo-500 to-purple-500",
    cyan: "from-cyan-500 to-blue-500",
    emerald: "from-emerald-500 to-teal-500",
    amber: "from-amber-500 to-orange-500",
    rose: "from-rose-500 to-pink-500",
  };

  const content = (
    <div className="group rounded-2xl bg-white border border-slate-200/60 p-5 shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-card-hover)] transition-all duration-300 hover:-translate-y-0.5">
      <div className="flex items-center justify-between mb-3">
        <div className={`h-10 w-10 rounded-xl bg-gradient-to-br ${colorMap[color] || colorMap.primary} flex items-center justify-center`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
        {trend && (
          <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
            {trend}
          </span>
        )}
      </div>
      <p className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-0.5">{label}</p>
      <h3 className="text-2xl font-serif font-bold text-ink">{value}</h3>
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }
  return content;
}

export function GradientBadge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-semibold text-white gradient-primary">
      {children}
    </span>
  );
}

export function StatusDot({ status }: { status: "online" | "warning" | "error" | "offline" }) {
  const colors = {
    online: "bg-emerald-500",
    warning: "bg-amber-500",
    error: "bg-rose-500",
    offline: "bg-slate-400",
  };
  return (
    <span className={`flex h-2 w-2 rounded-full ${colors[status]}`}>
      {status === "online" && (
        <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-emerald-400 opacity-75" />
      )}
    </span>
  );
}
