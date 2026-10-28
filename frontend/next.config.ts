import type { NextConfig } from "next";
import path from "path";

/**
 * Same-origin API (audit P0-5): the browser only ever talks to this app's
 * origin, and Next.js proxies the backend's routes. Session cookies become
 * first-party, so SameSite=Lax works, Safari stops looping on login, and
 * CORS preflights disappear. BACKEND_INTERNAL_URL is read when the rewrites
 * are built (at `next build`), so it must be set in the build environment.
 */
function backendUrl(): string {
  const url = process.env.BACKEND_INTERNAL_URL?.trim().replace(/\/+$/, "");
  if (url) return url;
  if (process.env.NODE_ENV === "production") {
    // Fail the build rather than proxy every API call to "undefined/api/...".
    throw new Error("BACKEND_INTERNAL_URL must be set to the backend's URL for a production build");
  }
  return "http://localhost:8000";
}

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },
  async rewrites() {
    const backend = backendUrl();
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/auth/:path*", destination: `${backend}/auth/:path*` },
      // FastAPI's own API docs, linked from the landing footer.
      { source: "/docs", destination: `${backend}/docs` },
      { source: "/redoc", destination: `${backend}/redoc` },
      { source: "/openapi.json", destination: `${backend}/openapi.json` },
    ];
  },
};

export default nextConfig;
