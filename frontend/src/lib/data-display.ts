export function metricLabel(count: number, loading: boolean, error: boolean, en: boolean, emptyLabel: string): string {
  if (loading) return en ? "Loading" : "加载中";
  if (error) return en ? "Unavailable" : "暂不可用";
  return count > 0 ? String(count) : emptyLabel;
}
