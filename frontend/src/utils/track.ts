const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 生成或读取访客 ID（基于浏览器指纹）
function getVisitorId(): string {
  if (typeof window === "undefined") return "server";
  let vid = localStorage.getItem("insight_visitor_id");
  if (!vid) {
    vid = "v_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("insight_visitor_id", vid);
  }
  return vid;
}

// 记录页面访问
export function trackPage(path: string) {
  if (typeof window === "undefined") return;
  const visitorId = getVisitorId();
  const ua = navigator.userAgent;

  // 使用 sendBeacon 优先（不阻塞页面卸载），降级用 fetch
  const payload = JSON.stringify({ page: path, visitor_id: visitorId, user_agent: ua });

  if (navigator.sendBeacon) {
    const blob = new Blob([payload], { type: "application/json" });
    navigator.sendBeacon(`${API}/api/track`, blob);
  } else {
    fetch(`${API}/api/track`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    }).catch(() => {});
  }
}
