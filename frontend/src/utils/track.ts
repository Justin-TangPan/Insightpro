import { API } from "@/lib/api";
import { optionalAuthenticatedFetch } from "@/lib/authenticated-fetch";

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
  const payload = JSON.stringify({ page: path, visitor_id: visitorId, user_agent: ua });
  void optionalAuthenticatedFetch(`${API}/api/track`, { method: "POST", headers: { "Content-Type": "application/json" }, body: payload, keepalive: true }).catch(() => undefined);
}
