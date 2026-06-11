import type { Metadata } from "next";
import { Cormorant_Garamond } from "next/font/google";
import "@fontsource/mona-sans/400.css";
import "@fontsource/mona-sans/500.css";
import "@fontsource/mona-sans/600.css";
import "@fontsource/mona-sans/700.css";
import "./globals.css";
import { Search, Bell } from "lucide-react";
import { Sidebar } from "@/components/sidebar";
import { MobileNavTrigger } from "@/components/mobile-nav";
import { PageTracker } from "@/components/page-tracker";
import Script from "next/script";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ['400', '500', '600', '700'],
  style: ['normal', 'italic'],
  variable: '--font-cormorant',
});

export const metadata: Metadata = {
  title: "InsightPro | 商业洞察平台",
  description: "AI 驱动的端到端商业洞察与分析平台",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh" className={cormorant.variable}>
      <body className="bg-surface text-ink antialiased" style={{ fontFamily: "'Mona Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" }}>
        <PageTracker />
        <div className="flex min-h-screen">
          <Sidebar />

          {/* Overlay for mobile */}
          <div id="sidebar-overlay" className="hidden fixed inset-0 bg-black/30 z-30 lg:hidden" />

          {/* Main */}
          <main className="flex-1 lg:pl-[250px]">
            {/* Header */}
            <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200/60">
              <div className="flex h-14 items-center justify-between px-4 lg:px-8">
                <div className="flex items-center gap-3">
                  <MobileNavTrigger />
                  <div className="flex items-center gap-2 bg-slate-50 px-3.5 py-1.5 rounded-lg border border-slate-200/60 w-60 lg:w-72 focus-within:border-slate-300 focus-within:bg-white transition-all">
                    <Search className="h-3.5 w-3.5 text-ink-muted" />
                    <input type="text" placeholder="搜索行业、竞品或历史报告..." className="bg-transparent border-none text-[13px] focus:outline-none w-full text-ink placeholder:text-ink-muted" />
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right hidden sm:block">
                    <p className="text-[10px] text-ink-muted font-medium uppercase tracking-wider">Today</p>
                    <p className="text-[13px] font-serif font-semibold text-ink">{new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
                  </div>
                  <div className="h-6 w-px bg-slate-200 hidden sm:block" />
                  <button className="relative h-8 w-8 rounded-lg bg-slate-50 border border-slate-200/60 flex items-center justify-center hover:bg-slate-100 transition-colors">
                    <Bell className="h-3.5 w-3.5 text-ink-secondary" />
                    <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-rose-500 border-[1.5px] border-white" />
                  </button>
                </div>
              </div>
            </header>

            <div className="p-6 lg:p-8 max-w-[1400px] mx-auto">{children}</div>
          </main>
        </div>
        <Script src="/chat.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
