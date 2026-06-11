/** Server-side backend URL (runtime env on Vercel — no rebuild needed). */
export function getBackendUrl(): string | null {
  const url =
    process.env.BILLGUARD_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

  if (!url) return null;
  return url.replace(/\/$/, "");
}

/** Client-side: use same-origin proxy on Vercel/production. */
export function getClientApiUrl(): string {
  if (typeof window === "undefined") {
    return getBackendUrl() || "http://localhost:8000";
  }
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return (
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    ).replace(/\/$/, "");
  }
  return "/backend";
}
