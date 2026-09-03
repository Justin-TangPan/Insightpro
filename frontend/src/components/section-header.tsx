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
    <section className="relative overflow-hidden rounded-2xl border border-grid/80 bg-surface-elevated">
      {image && (
        <div className="absolute inset-0 opacity-[0.04] grayscale">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={image} alt="" className="w-full h-full object-cover" />
        </div>
      )}

      <div className="relative px-6 py-7 md:px-8 md:py-8">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div className="max-w-3xl space-y-4">
            {badge && <GradientBadge>{badge}</GradientBadge>}
            <div className="editorial-rule opacity-80">
              <span className="editorial-rule__diamond" />
            </div>
            <h1 className="serif-display text-ink">
              {title}
            </h1>
            {subtitle && (
              <p className="max-w-2xl text-[0.9375rem] leading-6 text-ink-secondary">
                {subtitle}
              </p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      </div>
    </section>
  );
}
