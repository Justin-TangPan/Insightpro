"use client";

import { Menu } from "lucide-react";

export function MobileNavTrigger() {
  const toggle = () => {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    if (!sidebar) return;

    const isOpen = sidebar.classList.contains("translate-x-0");
    if (isOpen) {
      sidebar.classList.add("-translate-x-full");
      sidebar.classList.remove("translate-x-0");
      overlay?.classList.add("hidden");
    } else {
      sidebar.classList.remove("-translate-x-full");
      sidebar.classList.add("translate-x-0");
      overlay?.classList.remove("hidden");
    }
  };

  return (
    <button
      onClick={toggle}
      className="lg:hidden h-9 w-9 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center hover:bg-slate-100 transition-colors"
    >
      <Menu className="h-4 w-4 text-ink-secondary" />
    </button>
  );
}
