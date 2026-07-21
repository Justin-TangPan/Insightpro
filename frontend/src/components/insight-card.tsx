import { ReactNode } from "react";
import Link from "next/link";

interface InsightCardProps {
  children: ReactNode;
  className?: string;
  href?: string;
  glass?: boolean;
}

export function InsightCard({ children, className = "", href, glass = false }: InsightCardProps) {
  // 瑞士式：锐角、发丝线、无浮起，hover 加深边框
  const base = glass
    ? `glass p-6 ${className}`
    : `bg-white border border-grid p-6 transition-colors duration-200 hover:border-ink/30 ${className}`;

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
    <div className="flex items-center justify-between mb-6 pb-5 border-b border-grid">
      <h3 className="text-2xl serif-heading text-ink">{title}</h3>
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
  // 瑞士式：纯色 tile（去渐变），黑/柠檬/绿/橙轮换
  const tileMap: Record<string, string> = {
    primary: "bg-ink text-paper",
    cyan: "bg-lime text-ink",
    emerald: "bg-lime text-ink",
    amber: "bg-signal text-paper",
    rose: "bg-signal text-paper",
  };

  const content = (
    <div className="group bg-white border border-grid p-6 transition-colors duration-200 hover:border-ink/30">
      <div className="flex items-center justify-between mb-4">
        <div className={`h-10 w-10 flex items-center justify-center ${tileMap[color] || tileMap.primary}`}>
          <Icon className="h-5 w-5" />
        </div>
        {trend && (
          <span className="text-xs font-semibold text-ink bg-lemon px-2 py-0.5">
            {trend}
          </span>
        )}
      </div>
      <p className="swiss-kicker text-ink-muted mb-2">{label}</p>
      <h3 className="text-4xl serif-stat text-ink">{value}</h3>
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }
  return content;
}

export function GradientBadge({ children }: { children: ReactNode }) {
  // 瑞士式锐角标签：黑底白字 uppercase tracking
  return (
    <span className="inline-flex items-center px-3 py-1 bg-ink text-paper swiss-kicker">
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
