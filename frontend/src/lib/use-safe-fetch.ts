"use client";

import { useState } from "react";
import { authenticatedFetch } from "./authenticated-fetch";

/**
 * Standardized fetch hook with error state, loading indicator, and logging.
 * Replaces ad-hoc `.catch(() => undefined)` patterns with proper error surfacing.
 */
export function useSafeFetch<T>() {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const run = async (url: string, init?: RequestInit): Promise<T | null> => {
    setLoading(true);
    setError("");
    try {
      const res = await authenticatedFetch(url, init);
      if (!res.ok) {
        let detail = `请求失败 (${res.status})`;
        try {
          const body = await res.json();
          if (body?.detail) detail = body.detail;
        } catch { /* ignore parse error */ }
        throw new Error(detail);
      }
      const result: T = await res.json();
      setData(result);
      return result;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "请求失败";
      setError(msg);
      console.error("[useSafeFetch]", url, e);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { data, error, loading, run, setData };
}
