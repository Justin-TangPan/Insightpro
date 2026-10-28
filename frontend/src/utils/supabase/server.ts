import { createServerClient } from "@supabase/ssr";
import { authCookieOptions } from "./auth-cookie";

interface ServerCookie {
  name: string;
  value: string;
}

interface CookieStore {
  getAll(): ServerCookie[];
  set(name: string, value: string, options?: Record<string, unknown>): void;
}

export const createClient = (cookieStore: CookieStore) => {
  return createServerClient(
    process.env.SUPABASE_INTERNAL_URL || process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookieOptions: authCookieOptions,
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // The `setAll` method was called from a Server Component.
          }
        },
      },
    }
  );
};
