"use client";

import { FormEvent, useEffect, useState } from "react";
import { Search } from "lucide-react";
import { API } from "@/lib/api";
import { optionalAuthenticatedFetch } from "@/lib/authenticated-fetch";
import { usePreferences } from "@/lib/preferences";

type SearchSuggestion = { title: string; source: string };

export function SearchBar() {
  const { preferences } = usePreferences();
  const en = preferences.language === "en";
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  useEffect(() => {
    const value = query.trim();
    if (value.length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void optionalAuthenticatedFetch(`${API}/api/search?q=${encodeURIComponent(value)}&kind=all&page=1`, { signal: controller.signal })
        .then(async (response) => response.ok ? response.json() : { results: [] })
        .then((data: { results?: SearchSuggestion[] }) => setSuggestions((data.results || []).slice(0, 5)))
        .catch(() => undefined);
    }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [query]);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim()) window.location.href = `/search?q=${encodeURIComponent(query.trim())}`;
  };
  return (
    <form onSubmit={submit} role="search" className="ui-input flex w-60 items-center gap-2 px-3.5 lg:w-72">
      <Search className="h-4 w-4 text-ink-muted" />
      <input
        type="text"
        value={query}
        onChange={(event) => {
          const value = event.target.value;
          setQuery(value);
          if (value.trim().length < 2) setSuggestions([]);
        }}
        list="global-search-suggestions"
        placeholder={en ? "Search projects, solutions and AI apps..." : "搜索项目、方案、AI 应用…"}
        aria-label={en ? "Search projects, solutions and AI applications" : "全局搜索项目、方案和 AI 应用"}
        className="bg-transparent border-none text-sm focus:outline-none w-full text-ink placeholder:text-ink-muted"
        spellCheck={false}
        autoComplete="off"
      />
      <datalist id="global-search-suggestions">
        {suggestions.map((item) => <option key={`${item.source}-${item.title}`} value={item.title}>{item.source}</option>)}
      </datalist>
    </form>
  );
}
