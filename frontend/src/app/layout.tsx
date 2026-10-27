import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import { AuthProvider } from "@/components/auth-provider";
import { AppShell } from "@/components/app-shell";
import { InsightAgentShell } from "@/components/insight-agent-shell";
import { PageTracker } from "@/components/page-tracker";
import { ToastProvider } from "@/components/ui";

const inter = Inter({ subsets: ["latin"], weight: ["400", "500", "600", "700", "800"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: "小雷达 | AI 情报",
  description: "AI 产业热点、趋势与应用洞察雷达",
  icons: { icon: "/brand/xiaoleida.svg", apple: "/brand/xiaoleida.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="zh-CN" data-theme="light" className={inter.variable} suppressHydrationWarning>
    <head><script dangerouslySetInnerHTML={{ __html: `try{const p=JSON.parse(localStorage.getItem('insight_preferences')||'{}');document.documentElement.dataset.theme=p.theme==='dark'?'dark':'light'}catch{}` }} /></head>
    <body className="bg-paper text-ink antialiased"><AuthProvider><ToastProvider>
      <PageTracker />
      <AppShell>{children}</AppShell>
      <Suspense fallback={null}><InsightAgentShell /></Suspense>
    </ToastProvider></AuthProvider></body>
  </html>;
}
