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
    <div className="relative overflow-hidden bg-white border border-grid mb-10">
      {/* Optional hero image — 极淡，去色感 */}
      {image && (
        <div className="absolute inset-0 opacity-[0.06] grayscale">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={image} alt="" className="w-full h-full object-cover" />
        </div>
      )}

      <div className="relative px-8 lg:px-12 py-10 lg:py-14">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-5 max-w-3xl">
            {badge && <GradientBadge>{badge}</GradientBadge>}
            <div className="editorial-rule">
              <span className="editorial-rule__diamond" />
            </div>
            <h2 className="text-5xl md:text-6xl serif-display text-ink">
              {title}
            </h2>
            {subtitle && (
              <p className="text-base text-ink-secondary max-w-2xl leading-relaxed">
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
