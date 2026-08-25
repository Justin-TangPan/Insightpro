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
      aria-label="打开导航"
      className="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-ink-secondary shadow-[var(--shadow-card)] transition-colors hover:bg-primary-soft hover:text-primary lg:hidden"
    >
      <Menu className="h-4 w-4 text-ink-secondary" />
    </button>
  );
}
