import { type NextRequest, NextResponse } from "next/server";
import { updateSession } from "@/utils/supabase/middleware";

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  if (pathname === "/admin/login" || pathname.startsWith("/api/") || pathname === "/supabase" || pathname.startsWith("/supabase/") || ["/auth/register", "/auth/forgot-password", "/auth/reset-password"].includes(pathname)) return NextResponse.next();
  const { response, user } = await updateSession(request);
  if (user?.app_metadata?.role === "admin" && user.app_metadata?.status !== "disabled") return response;
  const login = new URL("/admin/login", request.url);
  login.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(login);
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js|woff2?)$).*)"] };
