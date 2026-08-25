import { ReactNode } from "react";
import Link from "next/link";

interface InsightCardProps {
  children: ReactNode;
  className?: string;
  href?: string;
  glass?: boolean;
}

export function InsightCard({ children, className = "", href, glass = false }: InsightCardProps) {
  const base = glass
    ? `glass ui-card ${className}`
    : `ui-card ${href ? "ui-card-interactive" : ""} ${className}`;

  if (href) {
    return (
      <Link href={href} className={`${base} block`}>
        {children}
      </Link>
    );
  }
  return <div className={base}>{children}</div>;
}

export function InsightCardHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="ui-card-header">
      <h3 className="type-h3 text-ink">{title}</h3>
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
  const tileMap: Record<string, string> = {
    primary: "bg-primary-soft text-primary",
    cyan: "bg-primary-soft text-primary",
    emerald: "bg-primary-soft text-primary",
    amber: "bg-warning-soft text-warning",
    rose: "bg-warning-soft text-warning",
  };

  const content = (
    <div className="ui-card ui-card-interactive group min-h-40">
      <div className="mb-7 flex items-start justify-between">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${tileMap[color] || tileMap.primary}`}>
          <Icon className="h-5 w-5" />
        </div>
        {trend && (
          <span className="ui-tag ui-tag-warning">
            {trend}
          </span>
        )}
      </div>
      <p className="swiss-kicker mb-2">{label}</p>
      <h3 className="text-4xl text-ink serif-stat">{value}</h3>
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }
  return content;
}

export function GradientBadge({ children }: { children: ReactNode }) {
  return (
    <span className="ui-tag font-mono uppercase tracking-[0.08em]">
      {children}
    </span>
  );
}

export function StatusDot({ status }: { status: "online" | "warning" | "error" | "offline" }) {
  const colors = {
    online: "bg-lime",
    warning: "bg-signal",
    error: "bg-signal",
    offline: "bg-ink-muted",
  };
  return (
    <span className={`flex h-2 w-2 rounded-full ${colors[status]}`}>
      {status === "online" && (
        <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-lime opacity-75" />
      )}
    </span>
  );
}
