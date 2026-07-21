import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Bell } from "lucide-react";
import { SearchBar } from "@/components/search-bar";
import { Sidebar } from "@/components/sidebar";
import { MobileNavTrigger } from "@/components/mobile-nav";
import { PageTracker } from "@/components/page-tracker";
import Script from "next/script";

const inter = Inter({
  subsets: ["latin"],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: "InsightPro | 商业洞察平台",
  description: "AI 驱动的端到端商业洞察与分析平台",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh" className={inter.variable}>
      <body className="bg-paper text-ink antialiased">
        <PageTracker />
        <div className="flex min-h-screen">
          <Sidebar />

          {/* Overlay for mobile */}
          <div id="sidebar-overlay" className="hidden fixed inset-0 bg-black/40 z-30 lg:hidden" />

          {/* Main */}
          <main className="flex-1 lg:pl-[250px]">
            {/* Header — 瑞士式发丝线顶栏 */}
            <header className="sticky top-0 z-10 bg-paper border-b border-grid">
              <div className="flex h-14 items-center justify-between px-4 lg:px-10">
                <div className="flex items-center gap-3">
                  <MobileNavTrigger />
                  <SearchBar />
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right hidden sm:block">
                    <p className="swiss-kicker text-ink-muted mb-0.5">Today</p>
                    <p className="text-sm font-semibold text-ink tracking-tight leading-tight">{new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
                  </div>
                  <div className="h-6 w-px bg-grid hidden sm:block" />
                  <button className="relative h-8 w-8 rounded-sm bg-white border border-grid flex items-center justify-center hover:border-ink/40 transition-colors">
                    <Bell className="h-3.5 w-3.5 text-ink-secondary" />
                    <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-signal border-[1.5px] border-paper" />
                  </button>
                </div>
              </div>
            </header>

            <div className="p-8 lg:p-12 max-w-[1440px] mx-auto">{children}</div>
          </main>
        </div>
        <Script src="/chat.js" strategy="afterInteractive" />
        <Script id="chat-api-config" strategy="beforeInteractive">
          {`window.__CHAT_API_URL__=window.location.origin;`}
        </Script>
      </body>
    </html>
  );
}
