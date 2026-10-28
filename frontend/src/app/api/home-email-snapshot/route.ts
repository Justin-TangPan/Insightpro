import { NextRequest } from "next/server";
import { readFileSync } from "node:fs";
import { selectRecentFocus, type FocusEvent } from "@/lib/home-focus";
import { businessNames, displayTitle, insightKinds, usefulSummary } from "@/lib/home-content";

export const dynamic = "force-dynamic";

type Event = FocusEvent & { image_url?: string };

export async function GET(request: NextRequest) {
  let secret = "";
  try { secret = readFileSync("/run/secrets/insight-hermes-gateway", "utf8").trim(); } catch { return new Response("Unavailable", { status: 503 }); }
  if (!secret || request.headers.get("x-insight-internal-key") !== secret) return new Response("Unauthorized", { status: 401 });
  const backend = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
  const response = await fetch(`${backend}/api/radar/intelligence`, { cache: "no-store", headers: { "x-insight-internal-key": secret } });
  if (!response.ok) return new Response("Homepage data unavailable", { status: 503 });
  const data = await response.json() as { as_of: string; events: Event[] };
  const keypoints = selectRecentFocus(data.events, data.as_of, 5);
  const asOf = Date.parse(data.as_of);
  const latest = data.events.filter(event => {
    const day = Date.parse(`${event.happened_at.slice(0, 10)}T00:00:00+08:00`);
    return Number.isFinite(day) && Number.isFinite(asOf) && asOf - day < 7 * 86400000 && asOf >= day;
  }).slice(0, 12);
  const mailFocus = (item: typeof keypoints[number]) => ({ ...item, event: { ...item.event, display_title: displayTitle(item.event), summary: usefulSummary(item.event) || "来源暂未提供发布摘要，请查看原始来源。", why: item.event.why || "可从来源内容核实其影响与后续采用情况。" } });
  return Response.json({ as_of: data.as_of, focus: keypoints[0] ? mailFocus(keypoints[0]) : null, keypoints: keypoints.slice(1).map(mailFocus),
    insights: insightKinds.map(kind => ({ label: kind.label, event: data.events.find(event => kind.match(event) && usefulSummary(event)) || null })),
    boards: ["github", "apps", "solutions", "community", "competitors"].map(key => ({ key, name: businessNames[key], events: data.events.filter(event => event.board === key).slice(0, 3) })),
    vendors: data.events.filter(event => event.board === "competitors").slice(0, 5), latest });
}
