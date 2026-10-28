import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const backend = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
      {
        source: "/supabase/:path*",
        destination: `${process.env.SUPABASE_INTERNAL_URL || "http://supabase-envoy:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
