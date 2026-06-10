import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "./backend-url";

// Vercel Hobby max is 60s — we retry within that window
export const maxDuration = 60;

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function proxyToBackend(
  request: NextRequest,
  backendPath: string
): Promise<NextResponse> {
  const backend = getBackendUrl();
  const url = `${backend}${backendPath}${request.nextUrl.search}`;

  const headers = new Headers();
  const requestContentType = request.headers.get("content-type");
  if (requestContentType) headers.set("Content-Type", requestContentType);
  const accept = request.headers.get("accept");
  if (accept) headers.set("Accept", accept);

  const body =
    request.method !== "GET" && request.method !== "HEAD"
      ? await request.arrayBuffer()
      : undefined;

  const attempts = 3;
  let lastError: Error | null = null;

  for (let i = 0; i < attempts; i++) {
    if (i > 0) await sleep(6000);

    const init: RequestInit = { method: request.method, headers };
    if (body) init.body = body;

    try {
      const upstream = await fetch(url, {
        ...init,
        signal: AbortSignal.timeout(50_000),
      });

      const upstreamContentType = upstream.headers.get("content-type") || "";
      if (upstreamContentType.includes("text/html")) {
        const html = await upstream.text();
        const isWrongApp =
          html.includes("Cannot POST") ||
          html.includes("Cannot GET") ||
          upstream.status === 404;
        return NextResponse.json(
          {
            detail: isWrongApp
              ? "Render backend is the wrong app (not BillGuard FastAPI)."
              : `Backend returned HTML error (${upstream.status}).`,
          },
          { status: 502 }
        );
      }

      const responseHeaders = new Headers();
      const upstreamType = upstream.headers.get("content-type");
      if (upstreamType) responseHeaders.set("Content-Type", upstreamType);
      responseHeaders.set("Cache-Control", "no-cache");

      return new NextResponse(upstream.body, {
        status: upstream.status,
        headers: responseHeaders,
      });
    } catch (err) {
      lastError = err instanceof Error ? err : new Error("Backend unreachable");
    }
  }

  return NextResponse.json(
    {
      detail:
        "Server is waking up (Render free tier). Wait 30 seconds and try again — " +
        "or refresh the page.",
      waking: true,
    },
    { status: 503 }
  );
}
