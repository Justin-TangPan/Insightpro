const entries = new Map<string, { value: unknown; time: number }>();
const pending = new Map<string, Promise<unknown>>();
const TTL = 60_000;

export function peekJson<T>(url: string): T | undefined {
  return entries.get(url)?.value as T | undefined;
}

export async function cachedJson<T>(url: string, force = false): Promise<T> {
  const entry = entries.get(url);
  if (!force && entry && Date.now() - entry.time < TTL) return entry.value as T;
  if (!force && pending.has(url)) return pending.get(url) as Promise<T>;
  const request = (async () => {
    const response = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(10_000) });
    if (!response.ok) throw new Error(`${url} (${response.status})`);
    const value = await response.json() as T;
    entries.set(url, { value, time: Date.now() });
    return value;
  })();
  pending.set(url, request);
  try { return await request; }
  finally { if (pending.get(url) === request) pending.delete(url); }
}
