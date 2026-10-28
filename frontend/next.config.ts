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

/**
 * Security headers (solutions doc, P2). connect-src 'self' works because
 * the API is same-origin (P0-5). 'unsafe-inline' for scripts is what Next.js
 * needs without nonces (a nonce middleware is deferred). The proxied
 * FastAPI docs (/docs, /redoc) load Swagger UI and ReDoc from a CDN, so the
 * CSP skips them; they still get the other three headers.
 */
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "img-src 'self' data: https://avatars.githubusercontent.com",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "connect-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self' https://github.com",
].join("; ");

const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  async headers() {
    return [
      { source: "/(.*)", headers: SECURITY_HEADERS },
      {
        source: "/((?!(?:docs|redoc)(?:/|$)).*)",
        headers: [{ key: "Content-Security-Policy", value: CONTENT_SECURITY_POLICY }],
      },
    ];
  },
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
