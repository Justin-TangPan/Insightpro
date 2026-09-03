export default function Loading() {
  return (
    <div className="space-y-5" role="status" aria-label="正在加载页面">
      <div className="h-32 animate-pulse rounded-2xl bg-surface-subtle" />
      <div className="grid gap-3 md:grid-cols-3">
        {[0, 1, 2].map((item) => <div key={item} className="h-40 animate-pulse rounded-xl bg-surface-subtle" />)}
      </div>
      <span className="sr-only">正在加载页面内容</span>
    </div>
  );
}
