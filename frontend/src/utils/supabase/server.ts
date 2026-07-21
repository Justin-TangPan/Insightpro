import { createServerClient } from "@supabase/ssr";

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
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
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
