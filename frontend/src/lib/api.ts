// Empty means same-origin. Next.js rewrites /api/* to the local FastAPI service.
export const API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
