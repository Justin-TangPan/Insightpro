"use client";

import { Search } from "lucide-react";

export function SearchBar() {
  return (
    <div className="ui-input flex w-60 items-center gap-2 px-3.5 lg:w-72">
      <Search className="h-4 w-4 text-ink-muted" />
      <input
        type="text"
        placeholder="搜索洞察、Requirements、Solutions..."
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
