import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

export async function POST(request: NextRequest) {
  const backend = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${backend}/api/agent/practice-background`, {
      method: "POST",
      headers: {
        "Content-Type": request.headers.get("content-type") || "application/json",
        Authorization: request.headers.get("authorization") || "",
      },
      body: await request.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(110_000),
    });
    return new NextResponse(response.body, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") || "application/json", "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "背景信息生成超时，请重试。" }, { status: 504 });
  }
}
