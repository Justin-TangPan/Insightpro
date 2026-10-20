import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SearchBar } from "@/components/search-bar";
import { HeaderDate } from "@/components/header-date";
import { Sidebar } from "@/components/sidebar";
import { MobileNavOverlay, MobileNavTrigger } from "@/components/mobile-nav";
import { PageTracker } from "@/components/page-tracker";
import { AuthProvider } from "@/components/auth-provider";
import { InsightAgentShell } from "@/components/insight-agent-shell";
import { Suspense } from "react";
import { ToastProvider } from "@/components/ui";

const inter = Inter({
  subsets: ["latin"],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: "InsightPro | AI Radar",
  description: "AI 产业热点、趋势与应用洞察雷达",
  icons: { icon: "/brand/insightpro-logo.png", apple: "/brand/insightpro-logo.png" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={inter.variable} suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: `try{const p=JSON.parse(localStorage.getItem('insight_preferences')||'{}'),r=document.documentElement;r.dataset.theme=p.theme==='light'?'light':'dark';r.dataset.density=p.density||'comfortable';r.dataset.motion=String(p.motion!==false);r.lang=p.language==='en'?'en':'zh-CN'}catch{}` }} /></head>
      <body className="bg-paper text-ink antialiased">
        <AuthProvider>
          <ToastProvider>
          <PageTracker />
          <div className="flex min-h-screen">
          <Sidebar />

          {/* Overlay for mobile */}
          <MobileNavOverlay />

          {/* Main */}
          <main id="app-main" className="min-w-0 flex-1">
            <header className="app-header sticky top-0 z-30">
              <div className="mx-auto flex h-16 max-w-[90rem] items-center justify-between px-[var(--page-gutter)]">
                <div className="flex items-center gap-3">
                  <MobileNavTrigger />
                  <SearchBar />
                </div>
                <div className="flex items-center gap-3">
                  <div className="hidden text-right sm:block">
                    <p className="swiss-kicker mb-0.5 text-ink-muted">TODAY</p>
                    <HeaderDate />
                  </div>
                  <div className="hidden h-6 w-px bg-grid sm:block" />
                  <a
                    href="https://github.com/Justin-TangPan/Insightpro"
                    target="_blank"
                    rel="noreferrer"
                    aria-label="打开 InsightPro GitHub 仓库"
                    className="ui-icon-button bg-white text-ink-secondary shadow-[var(--shadow-card)] hover:bg-primary-soft hover:text-primary"
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
                      <path d="M12 .75a11.25 11.25 0 0 0-3.56 21.92c.56.1.77-.24.77-.54v-2.1c-3.14.68-3.8-1.33-3.8-1.33-.51-1.3-1.25-1.65-1.25-1.65-1.02-.7.08-.69.08-.69 1.13.08 1.73 1.16 1.73 1.16 1 1.72 2.62 1.22 3.26.93.1-.73.39-1.22.71-1.5-2.5-.28-5.13-1.25-5.13-5.57 0-1.23.44-2.23 1.16-3.02-.12-.28-.5-1.43.11-2.98 0 0 .95-.3 3.1 1.15a10.8 10.8 0 0 1 5.64 0c2.15-1.46 3.1-1.15 3.1-1.15.61 1.55.23 2.7.11 2.98.72.79 1.16 1.79 1.16 3.02 0 4.33-2.64 5.29-5.15 5.57.4.35.76 1.04.76 2.1v3.08c0 .3.2.65.78.54A11.25 11.25 0 0 0 12 .75Z" />
                    </svg>
                  </a>
                </div>
              </div>
            </header>

            <div className="page-shell">{children}</div>
          </main>
          </div>
          <Suspense fallback={null}><InsightAgentShell /></Suspense>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
