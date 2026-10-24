import { ReactNode } from "react";
import { GradientBadge } from "./insight-card";

interface SectionHeaderProps {
  badge?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
  image?: string;
  compact?: boolean;
  icon?: ReactNode;
  className?: string;
}

export function SectionHeader({ badge, title, subtitle, action, image, compact, icon, className }: SectionHeaderProps) {
  if (compact) return <section className={`flex min-h-[4.25rem] items-center justify-between gap-3 rounded-xl border border-grid bg-surface-elevated/80 px-4 py-3 shadow-[var(--shadow-card)] ${className || ""}`}><div className="flex min-w-0 items-center gap-3">{icon && <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">{icon}</span>}<h1 className="truncate text-xl font-semibold tracking-tight text-ink">{title}</h1></div>{action && <div className="shrink-0">{action}</div>}</section>;
  return (
    <section className="relative overflow-hidden rounded-2xl border border-grid/80 bg-surface-elevated">
      {image && <div className="absolute inset-0 opacity-[0.04] grayscale">{/* eslint-disable-next-line @next/next/no-img-element */}<img src={image} alt="" className="h-full w-full object-cover" /></div>}
      <div className="relative px-5 py-4 md:px-6 md:py-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="max-w-3xl space-y-2">{badge && <GradientBadge>{badge}</GradientBadge>}<h1 className="type-h2 text-ink">{title}</h1>{subtitle && <p className="max-w-2xl text-[0.9375rem] leading-6 text-ink-secondary">{subtitle}</p>}</div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      </div>
    </section>
  );
}
