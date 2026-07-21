"use client";

import { Search } from "lucide-react";

export function SearchBar() {
  return (
    <div className="flex items-center gap-2 bg-white px-3.5 py-1.5 rounded-sm border border-grid w-60 lg:w-72 focus-within:border-ink/40 transition-colors">
      <Search className="h-3.5 w-3.5 text-ink-muted" />
      <input
        type="text"
        placeholder="搜索行业、竞品或历史报告..."
        className="bg-transparent border-none text-sm focus:outline-none w-full text-ink placeholder:text-ink-muted"
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            const v = (e.target as HTMLInputElement).value;
            if (v.trim()) window.location.href = `/search?q=${encodeURIComponent(v.trim())}`;
          }
        }}
      />
    </div>
  );
}
