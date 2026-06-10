import type { NextConfig } from "next";

const backendUrl = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    // Proxy API calls through Vercel → avoids CORS and localhost fallback in production
    if (!backendUrl || backendUrl.includes("localhost")) {
      return [];
    }
    return [
      { source: "/backend/health", destination: `${backendUrl}/health` },
      { source: "/backend/api/:path*", destination: `${backendUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;
