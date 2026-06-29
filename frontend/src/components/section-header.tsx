import { ReactNode } from "react";
import { GradientBadge } from "./insight-card";

interface SectionHeaderProps {
  badge?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
  image?: string;
}

export function SectionHeader({ badge, title, subtitle, action, image }: SectionHeaderProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-white border border-slate-200/60 shadow-[var(--shadow-card)] mb-8">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-50/50 via-transparent to-purple-50/30" />
      <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-indigo-100/20 to-transparent rounded-full blur-3xl" />

      {/* Optional hero image */}
      {image && (
        <div className="absolute inset-0 opacity-[0.07]">
          <img src={image} alt="" className="w-full h-full object-cover" />
        </div>
      )}

      <div className="relative px-10 py-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4 max-w-3xl">
            {badge && <GradientBadge>{badge}</GradientBadge>}
            <div className="editorial-rule">
              <span className="editorial-rule__diamond" />
            </div>
            <h2 className="text-4xl md:text-5xl serif-display text-ink">
              {title}
            </h2>
            {subtitle && (
              <p className="text-base text-ink-secondary max-w-2xl leading-loose">
                {subtitle}
              </p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      </div>
    </div>
  );
}
