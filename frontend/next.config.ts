import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * In development, proxy /api/* requests to the FastAPI backend to avoid
   * CORS and port-juggling. The WebSocket endpoint cannot be proxied via
   * Next.js rewrites (ws:// is unsupported); use NEXT_PUBLIC_WS_BASE_URL
   * to point the client-side WS hook directly at the backend.
   */
  async rewrites() {
    const backendUrl =
      process.env.BACKEND_URL?.replace(/\/$/, "") ?? "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },

  images: {
    remotePatterns: [
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
    ],
  },

  // Enable standalone output for the Docker build
  output: "standalone",
};

export default nextConfig;
